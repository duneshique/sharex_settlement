import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

import sys
from pathlib import Path

# Vercel 환경에서 경로 설정
BASE_PATH = Path(__file__).parent.parent
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

# ShareX 모듈 import (절대 경로 기준)
from server_logic.mvp.pdf_extractor import extract_pdf_data
from server_logic.mvp.settlement_calculator import calculate_settlements
from server_logic.api.email_service import EmailService

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    except Exception as e:
        print(f"Supabase init error: {e}")

class SaveArchiveRequest(BaseModel):
    period: str
    companies: Dict[str, Any]
    summary: Dict[str, Any]
    source_file: Optional[str] = ""
    remarks: Optional[Dict[str, str]] = {}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "env": "vercel"}

@app.post("/api/settlements/parse")
async def parse_settlement(file: UploadFile = File(...)):
    try:
        # Vercel 전용 임시 파일 경로
        file_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # 로직 실행 시 절대 경로 전달
        extracted_data = extract_pdf_data(file_path, str(LOGIC_PATH))
        settlement_result = calculate_settlements(extracted_data, str(LOGIC_PATH))

        return {
            "period": settlement_result["period"],
            "companies": settlement_result.get("companies", {}),
            "summary": {
                "total_revenue": extracted_data.get("total_revenue", 0),
                "total_ad_cost": extracted_data.get("total_ad_cost", 0),
                "total_settlement": settlement_result.get("total_settlement", 0),
            },
            "companies_info": {} # 필요시 추가 로드
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/archive/save")
async def save_archive(request: SaveArchiveRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        data = {
            "period": request.period,
            "saved_at": datetime.now().isoformat(),
            "data": request.dict(),
            "total_settlement": request.summary.get("total_settlement", 0),
            "company_count": len(request.companies)
        }
        supabase.table("archives").upsert(data).execute()
        return {"status": "saved", "period": request.period}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/archive/list")
async def list_archives():
    if not supabase:
        return {"archives": [], "error": "No DB"}
    try:
        res = supabase.table("archives").select("period, saved_at, company_count, total_settlement").order("saved_at", desc=True).execute()
        return {"archives": res.data, "count": len(res.data)}
    except Exception as e:
        return {"archives": [], "error": str(e)}

@app.get("/api/archive/{period}")
async def get_archive(period: str):
    if not supabase:
        raise HTTPException(status_code=404)
    res = supabase.table("archives").select("data").eq("period", period).execute()
    if res.data:
        return res.data[0]["data"]
    raise HTTPException(status_code=404)
