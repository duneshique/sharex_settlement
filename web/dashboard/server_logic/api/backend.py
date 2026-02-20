"""
ShareX 정산 시스템 - FastAPI 백엔드

웹 UI 중심 아키텍처:
1. PDF 업로드 → 빠른 파싱 (0.34초)
2. 정산 계산 → JSON 반환
3. 웹에서 실시간 수정 가능
4. 최종 승인 → PDF 생성 → 이메일 발송
"""

import os
import json
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from supabase import create_client, Client

# ShareX 모듈 import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mvp.pdf_extractor import extract_pdf_data
from src.mvp.settlement_calculator import calculate_settlements
from src.mvp.pdf_generator import generate_all_settlement_pdfs, generate_single_company_pdf, get_pdf_filename
from src.api.email_service import EmailService, log_email_to_archive

# FastAPI 앱 생성
app = FastAPI(
    title="ShareX Settlement API",
    description="정산서 생성 및 관리 API",
    version="2.0.0"
)

# CORS 설정 (웹 UI 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 배포 환경을 위해 모든 오리진 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase 클라이언트 초기화 완료")
    except Exception as e:
        print(f"❌ Supabase 초기화 실패: {e}")

# 설정
BASE_PATH = Path(__file__).parent.parent.parent
UPLOAD_DIR = BASE_PATH / "uploads"
OUTPUT_DIR = BASE_PATH / "output"
CONFIG_DIR = BASE_PATH / "config"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 백그라운드 작업 관리
pdf_tasks: Dict[str, Dict[str, Any]] = {}
executor = ThreadPoolExecutor(max_workers=4)

# 기업 정보 캐시
companies_data: Dict[str, Any] = {}

# 이메일 서비스
email_service: Optional[EmailService] = None


# ============================================================================
# Pydantic 모델
# ============================================================================

class GeneratePdfRequest(BaseModel):
    """PDF 생성 요청 스키마"""
    period: str
    settlement_data: Dict[str, Any]


class SaveArchiveRequest(BaseModel):
    """아카이브 저장 요청"""
    period: str
    companies: Dict[str, Any]
    summary: Dict[str, Any]
    source_file: Optional[str] = ""
    remarks: Optional[Dict[str, str]] = {}


class ApprovalRequest(BaseModel):
    """승인/해제 요청"""
    period: str
    company_id: str


class EmailSendRequest(BaseModel):
    """개별 이메일 발송 요청"""
    period: str
    company_id: str
    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class BulkEmailSendRequest(BaseModel):
    """일괄 이메일 발송 요청"""
    period: str
    company_ids: List[str]
    subject_template: Optional[str] = None
    body_template: Optional[str] = None


class SmtpConfigRequest(BaseModel):
    """SMTP 설정"""
    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    sender_name: str = "플러스엑스 정산팀"
    sender_email: str = "finance@plus-ex.com"


class EmailTemplateRequest(BaseModel):
    """이메일 템플릿"""
    subject: str
    body: str


class SinglePdfRequest(BaseModel):
    """단일 기업 PDF 생성 요청"""
    period: str
    company_id: str


# ============================================================================
# 초기화
# ============================================================================

def _load_companies_data():
    """기업 정보 로드"""
    global companies_data
    companies_path = BASE_PATH / "data" / "companies.json"
    if companies_path.exists():
        with open(companies_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for company in data.get("companies", []):
                companies_data[company["company_id"]] = company


def _init_email_service():
    """이메일 서비스 초기화"""
    global email_service
    email_service = EmailService(str(CONFIG_DIR))


def _generate_pdfs_background(settlement_result: Dict, output_dir: str):
    """백그라운드 PDF 생성"""
    try:
        results = generate_all_settlement_pdfs(settlement_result, output_dir, companies_data)
        return {"status": "completed", "results": results}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def _load_archive(period: str) -> Dict[str, Any]:
    """아카이브 JSON 로드 (내부 헬퍼)"""
    archive_file = ARCHIVE_DIR / f"{period}.json"
    if not archive_file.exists():
        raise HTTPException(status_code=404, detail=f"{period} 아카이브를 찾을 수 없습니다")
    with open(archive_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_archive_data(period: str, data: Dict[str, Any]) -> None:
    """아카이브 JSON 저장 (내부 헬퍼)"""
    archive_file = ARCHIVE_DIR / f"{period}.json"
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.on_event("startup")
async def startup_event():
    """시작 시 초기화"""
    _load_companies_data()
    _init_email_service()
    print("✅ ShareX Settlement API 시작")
    print(f"   - 기업 정보: {len(companies_data)}개 로드됨")
    print(f"   - SMTP 설정: {'완료' if email_service and email_service.smtp_config.get('username') else '미설정'}")


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================================================
# PDF 업로드 & 파싱
# ============================================================================

@app.post("/api/settlements/parse")
async def parse_settlement(file: UploadFile = File(...)) -> Dict[str, Any]:
    """PDF 파일 업로드 및 빠른 파싱"""
    try:
        file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        extracted_data = extract_pdf_data(str(file_path), str(BASE_PATH))
        settlement_result = calculate_settlements(extracted_data, str(BASE_PATH))

        response = {
            "period": settlement_result["period"],
            "extraction_date": datetime.now().isoformat(),
            "courses": extracted_data.get("courses", []),
            "course_count": extracted_data.get("course_count", 0),
            "companies": settlement_result.get("companies", {}),
            "company_count": len(settlement_result.get("companies", {})),
            "summary": {
                "total_revenue": extracted_data.get("total_revenue", 0),
                "total_ad_cost": extracted_data.get("total_ad_cost", 0),
                "total_contribution": extracted_data.get("total_contribution", 0),
                "total_settlement": settlement_result.get("total_settlement", 0),
            },
            "source_file": extracted_data.get("source_file", ""),
            "has_monthly_breakdown": extracted_data.get("has_monthly_breakdown", False),
            "companies_info": companies_data,
        }

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"PDF 파싱 실패: {str(e)}")


# ============================================================================
# PDF 생성 (백그라운드 일괄 + 단일)
# ============================================================================

@app.post("/api/settlements/generate-pdf")
async def generate_pdf_background(request: GeneratePdfRequest) -> Dict[str, Any]:
    """백그라운드 PDF 일괄 생성"""
    try:
        task_id = str(uuid.uuid4())
        output_dir = str(OUTPUT_DIR / request.period)

        pdf_tasks[task_id] = {
            "status": "queued",
            "period": request.period,
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "results": None,
        }

        def generate_task():
            try:
                pdf_tasks[task_id]["status"] = "processing"
                pdf_tasks[task_id]["progress"] = 50
                result = _generate_pdfs_background(request.settlement_data, output_dir)
                pdf_tasks[task_id]["status"] = result["status"]
                pdf_tasks[task_id]["progress"] = 100
                pdf_tasks[task_id]["results"] = result.get("results", [])
            except Exception as e:
                pdf_tasks[task_id]["status"] = "failed"
                pdf_tasks[task_id]["error"] = str(e)

        executor.submit(generate_task)

        return {"task_id": task_id, "status": "queued", "message": "PDF 생성이 백그라운드에서 진행 중입니다"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/settlements/generate-single-pdf")
async def generate_single_pdf(request: SinglePdfRequest) -> Dict[str, Any]:
    """단일 기업 PDF 생성 (동기)"""
    try:
        archive_data = _load_archive(request.period)
        company_settlement = archive_data.get("companies", {}).get(request.company_id)
        if not company_settlement:
            raise HTTPException(status_code=404, detail=f"기업 {request.company_id}의 정산 데이터가 없습니다")

        company_info = companies_data.get(request.company_id, {})
        output_dir = str(OUTPUT_DIR / request.period)

        pdf_path = generate_single_company_pdf(
            period=request.period,
            company_id=request.company_id,
            settlement_data=company_settlement,
            company_info=company_info,
            output_dir=output_dir,
        )

        return {
            "status": "completed",
            "pdf_file": Path(pdf_path).name,
            "pdf_path": pdf_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/settlements/status/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """PDF 생성 작업 상태 확인"""
    if task_id not in pdf_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    task = pdf_tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task.get("progress", 0),
        "results": task.get("results", []),
        "error": task.get("error", None),
        "created_at": task.get("created_at"),
    }


# ============================================================================
# 파일 다운로드
# ============================================================================

@app.get("/api/settlements/download/{period}/{filename}")
async def download_pdf(period: str, filename: str):
    """생성된 PDF 파일 다운로드"""
    try:
        file_path = OUTPUT_DIR / period / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        return FileResponse(str(file_path), media_type="application/pdf", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 아카이브 관리
# ============================================================================

ARCHIVE_DIR = BASE_PATH / "data" / "archive"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/archive/save")
async def save_archive(request: SaveArchiveRequest) -> Dict[str, Any]:
    """정산 데이터 저장 (기존 approval_status, email_log 보존)"""
    try:
        archive_file = ARCHIVE_DIR / f"{request.period}.json"

        # 기존 아카이브에서 approval_status, email_log 보존
        existing_approval = {}
        existing_email_log = {}
        if archive_file.exists():
            with open(archive_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
                existing_approval = existing.get("approval_status", {})
                existing_email_log = existing.get("email_log", {})

        archive_data = {
            "period": request.period,
            "saved_at": datetime.now().isoformat(),
            "companies": request.companies,
            "summary": request.summary,
            "source_file": request.source_file,
            "remarks": request.remarks,
            "companies_info": {k: v for k, v in companies_data.items()},
            "approval_status": existing_approval,
            "email_log": existing_email_log,
        }

        if supabase:
            try:
                # DB 저장 (upsert)
                supabase.table("archives").upsert({
                    "period": request.period,
                    "saved_at": archive_data["saved_at"],
                    "data": archive_data,
                    "total_settlement": request.summary.get("total_settlement", 0),
                    "company_count": len(request.companies)
                }).execute()
                print(f"✅ Supabase DB에 아카이브 저장 완료: {request.period}")
            except Exception as e:
                print(f"⚠️ Supabase 저장 실패 (로컬 저장은 완료): {e}")

        return {
            "status": "saved",
            "period": request.period,
            "file": str(archive_file),
            "database": "synced" if supabase else "local_only",
            "saved_at": archive_data["saved_at"],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/archive/list")
async def list_archives() -> Dict[str, Any]:
    """저장된 아카이브 목록 조회 (Supabase 우선, 로컬 보조)"""
    archives = []
    
    # 1. Supabase에서 먼저 조회
    if supabase:
        try:
            response = supabase.table("archives").select("period, saved_at, company_count, total_settlement").order("saved_at", desc=True).execute()
            archives = response.data
            if archives:
                return {"archives": archives, "count": len(archives), "source": "database"}
        except Exception as e:
            print(f"⚠️ Supabase 목록 조회 실패: {e}")

    # 2. 로컬 파일 보조 (Supabase 실패 시)
    for f in sorted(ARCHIVE_DIR.glob("*.json"), reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                approval = data.get("approval_status", {})
                approved_count = sum(1 for v in approval.values() if v.get("approved"))
                archives.append({
                    "period": data.get("period", f.stem),
                    "saved_at": data.get("saved_at", ""),
                    "company_count": len(data.get("companies", {})),
                    "total_settlement": data.get("summary", {}).get("total_settlement", 0),
                    "approved_count": approved_count,
                })
        except Exception:
            continue

    return {"archives": archives, "count": len(archives), "source": "local"}


@app.get("/api/archive/{period}")
async def get_archive(period: str) -> Dict[str, Any]:
    """특정 기간의 아카이브 데이터 로드 (Supabase 우선)"""
    # 1. Supabase에서 조회
    if supabase:
        try:
            response = supabase.table("archives").select("data").eq("period", period).execute()
            if response.data:
                return response.data[0]["data"]
        except Exception as e:
            print(f"⚠️ Supabase 상세 로드 실패: {e}")

    # 2. 로컬 파일 보조
    return _load_archive(period)


# ============================================================================
# 승인 관리
# ============================================================================

@app.post("/api/archive/approve")
async def approve_company(request: ApprovalRequest) -> Dict[str, Any]:
    """기업 승인 + 단일 PDF 생성"""
    try:
        archive_data = _load_archive(request.period)

        # 기업 데이터 확인
        company_settlement = archive_data.get("companies", {}).get(request.company_id)
        if not company_settlement:
            raise HTTPException(status_code=404, detail=f"기업 {request.company_id}의 정산 데이터가 없습니다")

        # 승인 상태 설정
        if "approval_status" not in archive_data:
            archive_data["approval_status"] = {}

        archive_data["approval_status"][request.company_id] = {
            "approved": True,
            "approved_at": datetime.now().isoformat(),
            "approved_by": "admin",
        }

        _save_archive_data(request.period, archive_data)

        # 단일 PDF 생성
        company_info = companies_data.get(request.company_id, {})
        output_dir = str(OUTPUT_DIR / request.period)
        pdf_file = ""

        try:
            pdf_path = generate_single_company_pdf(
                period=request.period,
                company_id=request.company_id,
                settlement_data=company_settlement,
                company_info=company_info,
                output_dir=output_dir,
            )
            pdf_file = Path(pdf_path).name
        except Exception as e:
            print(f"⚠️ PDF 생성 실패 (승인은 완료): {e}")

        return {
            "status": "approved",
            "company_id": request.company_id,
            "approved_at": archive_data["approval_status"][request.company_id]["approved_at"],
            "pdf_file": pdf_file,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/archive/unapprove")
async def unapprove_company(request: ApprovalRequest) -> Dict[str, Any]:
    """기업 승인 해제"""
    try:
        archive_data = _load_archive(request.period)

        if "approval_status" not in archive_data:
            archive_data["approval_status"] = {}

        archive_data["approval_status"][request.company_id] = {
            "approved": False,
            "approved_at": None,
            "approved_by": None,
        }

        _save_archive_data(request.period, archive_data)

        return {
            "status": "unapproved",
            "company_id": request.company_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/archive/{period}/approval-status")
async def get_approval_status(period: str) -> Dict[str, Any]:
    """전체 승인 상태 조회"""
    try:
        archive_data = _load_archive(period)
        return archive_data.get("approval_status", {})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 이메일 발송
# ============================================================================

@app.post("/api/settlements/send-email")
async def send_settlement_email(request: EmailSendRequest) -> Dict[str, Any]:
    """개별 기업 이메일 발송"""
    if not email_service:
        raise HTTPException(status_code=500, detail="이메일 서비스가 초기화되지 않았습니다")

    try:
        # 아카이브 로드
        archive_data = _load_archive(request.period)

        # 승인 상태 확인
        approval = archive_data.get("approval_status", {}).get(request.company_id, {})
        if not approval.get("approved"):
            raise HTTPException(status_code=400, detail=f"기업 {request.company_id}이(가) 아직 승인되지 않았습니다. 먼저 승인을 완료하세요.")

        # 기업 데이터
        company_settlement = archive_data.get("companies", {}).get(request.company_id)
        if not company_settlement:
            raise HTTPException(status_code=404, detail=f"기업 {request.company_id}의 정산 데이터가 없습니다")

        company_info = companies_data.get(request.company_id, {})

        # PDF 파일 경로
        company_name = company_info.get("name", company_settlement.get("company_name", request.company_id))
        pdf_filename = get_pdf_filename(request.period, company_name)
        pdf_path = str(OUTPUT_DIR / request.period / pdf_filename)

        if not Path(pdf_path).exists():
            # PDF가 없으면 생성 시도
            try:
                generate_single_company_pdf(
                    period=request.period,
                    company_id=request.company_id,
                    settlement_data=company_settlement,
                    company_info=company_info,
                    output_dir=str(OUTPUT_DIR / request.period),
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"PDF 파일이 없고 생성도 실패했습니다: {e}")

        # 이메일 발송
        result = email_service.send_settlement_email(
            period=request.period,
            company_id=request.company_id,
            settlement_data=company_settlement,
            company_info=company_info,
            pdf_path=pdf_path,
            subject_override=request.subject,
            body_override=request.body,
            recipient_override=request.recipient_email,
        )

        # 발송 로그 저장
        log_entry = {
            "sent_at": result["sent_at"],
            "recipient": result["recipient"],
            "subject": result["subject"],
            "status": "sent",
            "pdf_filename": result.get("pdf_filename", ""),
        }
        archive_file = str(ARCHIVE_DIR / f"{request.period}.json")
        log_email_to_archive(archive_file, request.company_id, log_entry)

        return {"status": "sent", **result}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"이메일 발송 실패: {str(e)}")


@app.post("/api/settlements/send-bulk-email")
async def send_bulk_email(request: BulkEmailSendRequest) -> Dict[str, Any]:
    """일괄 이메일 발송"""
    if not email_service:
        raise HTTPException(status_code=500, detail="이메일 서비스가 초기화되지 않았습니다")

    try:
        archive_data = _load_archive(request.period)
        results = {}

        for company_id in request.company_ids:
            try:
                # 승인 확인
                approval = archive_data.get("approval_status", {}).get(company_id, {})
                if not approval.get("approved"):
                    results[company_id] = f"미승인 (승인 먼저 필요)"
                    continue

                company_settlement = archive_data.get("companies", {}).get(company_id)
                if not company_settlement:
                    results[company_id] = "정산 데이터 없음"
                    continue

                company_info = companies_data.get(company_id, {})
                company_name = company_info.get("name", company_settlement.get("company_name", company_id))

                # PDF 파일 확인/생성
                pdf_filename = get_pdf_filename(request.period, company_name)
                pdf_path = str(OUTPUT_DIR / request.period / pdf_filename)

                if not Path(pdf_path).exists():
                    try:
                        generate_single_company_pdf(
                            period=request.period,
                            company_id=company_id,
                            settlement_data=company_settlement,
                            company_info=company_info,
                            output_dir=str(OUTPUT_DIR / request.period),
                        )
                    except Exception as e:
                        results[company_id] = f"PDF 생성 실패: {e}"
                        continue

                # 이메일 발송
                result = email_service.send_settlement_email(
                    period=request.period,
                    company_id=company_id,
                    settlement_data=company_settlement,
                    company_info=company_info,
                    pdf_path=pdf_path,
                    subject_override=request.subject_template,
                    body_override=request.body_template,
                )

                # 로그 저장
                log_entry = {
                    "sent_at": result["sent_at"],
                    "recipient": result["recipient"],
                    "subject": result["subject"],
                    "status": "sent",
                    "pdf_filename": result.get("pdf_filename", ""),
                }
                archive_file = str(ARCHIVE_DIR / f"{request.period}.json")
                log_email_to_archive(archive_file, company_id, log_entry)

                results[company_id] = "sent"

            except Exception as e:
                results[company_id] = f"실패: {str(e)}"

        sent_count = sum(1 for v in results.values() if v == "sent")
        return {
            "status": "completed",
            "results": results,
            "sent_count": sent_count,
            "total_count": len(request.company_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 설정 관리 (SMTP + 이메일 템플릿)
# ============================================================================

@app.get("/api/settings/smtp")
async def get_smtp_config() -> Dict[str, Any]:
    """SMTP 설정 조회 (비밀번호 마스킹)"""
    if not email_service:
        return {"configured": False}
    return email_service.get_smtp_config_masked()


@app.post("/api/settings/smtp")
async def save_smtp_config(request: SmtpConfigRequest) -> Dict[str, Any]:
    """SMTP 설정 저장"""
    if not email_service:
        raise HTTPException(status_code=500, detail="이메일 서비스가 초기화되지 않았습니다")

    config = {
        "host": request.host,
        "port": request.port,
        "username": request.username,
        "password": request.password,
        "use_tls": request.use_tls,
        "sender_name": request.sender_name,
        "sender_email": request.sender_email,
    }
    email_service.save_smtp_config(config)
    return {"status": "saved", "message": "SMTP 설정이 저장되었습니다"}


@app.post("/api/settings/smtp/test")
async def test_smtp() -> Dict[str, Any]:
    """SMTP 연결 테스트"""
    if not email_service:
        raise HTTPException(status_code=500, detail="이메일 서비스가 초기화되지 않았습니다")
    return email_service.test_connection()


@app.get("/api/settings/email-template")
async def get_email_template() -> Dict[str, Any]:
    """이메일 템플릿 조회"""
    if not email_service:
        return EmailService._default_template()
    return email_service.get_template()


@app.post("/api/settings/email-template")
async def save_email_template(request: EmailTemplateRequest) -> Dict[str, Any]:
    """이메일 템플릿 저장"""
    if not email_service:
        raise HTTPException(status_code=500, detail="이메일 서비스가 초기화되지 않았습니다")

    email_service.save_template({
        "subject": request.subject,
        "body": request.body,
    })
    return {"status": "saved", "message": "이메일 템플릿이 저장되었습니다"}


# ============================================================================
# 루트
# ============================================================================

@app.get("/")
async def root():
    """API 정보"""
    return {
        "message": "ShareX Settlement API v2.0.0",
        "docs": "/docs",
        "api_endpoints": {
            "parse": "POST /api/settlements/parse",
            "generate_pdf": "POST /api/settlements/generate-pdf",
            "generate_single_pdf": "POST /api/settlements/generate-single-pdf",
            "status": "GET /api/settlements/status/{task_id}",
            "download": "GET /api/settlements/download/{period}/{filename}",
            "send_email": "POST /api/settlements/send-email",
            "send_bulk_email": "POST /api/settlements/send-bulk-email",
            "archive_save": "POST /api/archive/save",
            "archive_list": "GET /api/archive/list",
            "archive_load": "GET /api/archive/{period}",
            "approve": "POST /api/archive/approve",
            "unapprove": "POST /api/archive/unapprove",
            "approval_status": "GET /api/archive/{period}/approval-status",
            "smtp_config": "GET/POST /api/settings/smtp",
            "smtp_test": "POST /api/settings/smtp/test",
            "email_template": "GET/POST /api/settings/email-template",
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
