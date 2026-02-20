"""
MVP Step 1: PDF 데이터 추출

패스트캠퍼스 정산서 PDF에서 데이터를 추출합니다.
기존 parsers 모듈을 재사용하여 간단한 인터페이스를 제공합니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

from server_logic.parsers.fastcampus_pdf import parse_quarterly_pdf, parse_monthly_pdf, detect_period_from_filename
from server_logic.parsers.unified_pdf_parser import parse_settlement_pdf_unified
from server_logic.parsers.base import ParsedSettlementData, CourseSettlementRow, CourseSales, parse_quarter_months


def extract_pdf_data(pdf_path: str, base_path: str = None) -> Dict[str, Any]:
    """
    PDF에서 데이터 추출 (MVP 간소화 버전)

    Args:
        pdf_path: PDF 파일 경로
        base_path: 프로젝트 루트 경로 (기본값: pdf_path의 상위 디렉토리)

    Returns:
        {
            "period": "2024-Q4",
            "source_file": "...",
            "courses": [
                {
                    "course_id": "210001",
                    "course_name": "포토샵 완전정복",
                    "revenue": 15000000,
                    "ad_cost": 500000,
                    "contribution": 14500000,
                    "revenue_share": 10150000,
                    "section": "union",
                    "rs_ratio": 0.75
                }
            ],
            "total_revenue": 100000000,
            "total_ad_cost": 20000000,
            "total_contribution": 80000000
        }
    """
    # 기본 경로 설정
    if base_path is None:
        base_path = str(Path(pdf_path).parent.parent.parent)

    # 파일명에서 기간 자동 감지
    period_type, period = detect_period_from_filename(pdf_path)

    if period_type == "unknown":
        raise ValueError(
            f"PDF 파일명에서 기간을 인식할 수 없습니다: {pdf_path}\n"
            f"'YYYY년 NQ', 'YYYY년 N분기', 또는 'YYYY년 MM월' 형식이 필요합니다."
        )

    # 분기별 / 월별 분기 처리
    if period_type == "quarterly":
        # 통합 파서로 파싱 (양식 자동 감지)
        try:
            parsed: ParsedSettlementData = parse_settlement_pdf_unified(pdf_path, period, base_path)
        except Exception as e:
            # Fallback: 기존 파서
            print(f"통합 파서 실패, 기존 파서로 시도: {e}")
            parsed: ParsedSettlementData = parse_quarterly_pdf(pdf_path, period, base_path)
    elif period_type == "monthly":
        # 월별 파서 사용
        parsed: ParsedSettlementData = parse_monthly_pdf(pdf_path, period, base_path)
    else:
        raise ValueError(f"지원하지 않는 기간 유형: {period_type}")

    # MVP 형식으로 변환
    courses = []
    total_revenue = 0.0
    total_ad_cost = 0.0
    total_contribution = 0.0

    for row in parsed.settlement_rows:
        course_data = {
            "course_id": row.course_id,
            "course_name": row.course_name,
            "revenue": row.revenue,
            "ad_cost": row.ad_cost,
            "contribution": row.contribution_margin,
            "revenue_share": row.revenue_share_fee,
            "section": row.section,
            "rs_ratio": row.rs_ratio,
        }
        courses.append(course_data)

        total_revenue += row.revenue
        total_ad_cost += row.ad_cost
        total_contribution += row.contribution_margin

    result = {
        "period": period,
        "source_file": pdf_path,
        "extraction_date": parsed.metadata.get("extraction_date", ""),
        "courses": courses,
        "total_revenue": round(total_revenue, 2),
        "total_ad_cost": round(total_ad_cost, 2),
        "total_contribution": round(total_contribution, 2),
        "course_count": len(courses),
    }

    return result


def extract_monthly_pdf_data(pdf_path: str, month: str, base_path: str = None) -> Dict[str, Any]:
    """
    단일 월별 PDF에서 강의별 매출 추출

    Args:
        pdf_path: 월별 PDF 파일 경로
        month: 정산월 (예: "2024-10")
        base_path: 프로젝트 루트

    Returns:
        {"month": "2024-10", "courses": [{"course_id": ..., "revenue": ..., "month": ...}]}
    """
    if base_path is None:
        base_path = str(Path(pdf_path).parent.parent.parent)

    parsed: ParsedSettlementData = parse_monthly_pdf(pdf_path, month, base_path)

    courses = []
    for sale in parsed.course_sales:
        courses.append({
            "course_id": sale.course_id,
            "course_name": sale.course_name,
            "month": sale.month,
            "revenue": sale.revenue,
            "company_id": sale.company_id,
        })

    return {
        "month": month,
        "source_file": pdf_path,
        "courses": courses,
        "course_count": len(courses),
    }


def extract_quarterly_with_monthly(
    quarterly_pdf_path: str,
    monthly_pdf_paths: Dict[str, str],
    period: str,
    base_path: str = None,
) -> Dict[str, Any]:
    """
    분기 PDF (정본) + 월별 PDF 3개를 병합하여 월별 breakdown 포함 데이터 생성

    Args:
        quarterly_pdf_path: 분기 PDF 경로 (정산 금액의 정본)
        monthly_pdf_paths: {month: pdf_path} (예: {"2024-10": "/path/to/oct.pdf"})
        period: 분기 기간 (예: "2024-Q4")
        base_path: 프로젝트 루트

    Returns:
        extract_pdf_data()와 동일 구조 + 각 course에 monthly_revenue 필드 추가
    """
    # 1. 분기 PDF에서 정본 데이터 추출
    quarterly_data = extract_pdf_data(quarterly_pdf_path, base_path)

    # 2. 월별 PDF에서 강의별 월 매출 추출
    monthly_revenues = {}  # {course_id: {month: revenue}}
    for month, pdf_path in sorted(monthly_pdf_paths.items()):
        try:
            monthly_data = extract_monthly_pdf_data(pdf_path, month, base_path)
            for course in monthly_data["courses"]:
                cid = course["course_id"]
                if cid not in monthly_revenues:
                    monthly_revenues[cid] = {}
                monthly_revenues[cid][month] = course["revenue"]
        except Exception as e:
            print(f"  ⚠️  {month} 월별 PDF 파싱 실패: {e}")

    # 3. 분기 데이터에 월별 breakdown 병합
    for course in quarterly_data["courses"]:
        cid = course["course_id"]
        course["monthly_revenue"] = monthly_revenues.get(cid, {})

    quarterly_data["has_monthly_breakdown"] = True
    quarterly_data["monthly_sources"] = {
        month: Path(p).name for month, p in monthly_pdf_paths.items()
    }

    return quarterly_data


def save_extracted_data(data: Dict[str, Any], output_path: str) -> None:
    """
    추출된 데이터를 JSON 파일로 저장

    Args:
        data: extract_pdf_data()의 반환값
        output_path: 저장할 JSON 파일 경로
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 데이터 추출 완료: {output_file}")
    print(f"   - 기간: {data['period']}")
    print(f"   - 강의 수: {data['course_count']}")
    print(f"   - 총 매출: {data['total_revenue']:,.0f}원")
    print(f"   - 총 광고비: {data['total_ad_cost']:,.0f}원")


def load_extracted_data(json_path: str) -> Dict[str, Any]:
    """
    저장된 추출 데이터 로드

    Args:
        json_path: JSON 파일 경로

    Returns:
        extract_pdf_data()와 동일한 형식의 딕셔너리
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────
# 검증 함수
# ─────────────────────────────────────────────────────────

def validate_extraction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    추출 데이터 검증

    Returns:
        {
            "valid": True/False,
            "errors": [...],
            "warnings": [...]
        }
    """
    errors = []
    warnings = []

    # 1. 필수 필드 확인
    required_fields = ["period", "courses", "total_revenue"]
    for field in required_fields:
        if field not in data:
            errors.append(f"필수 필드 누락: {field}")

    # 2. 강의 데이터 확인
    if "courses" in data:
        if len(data["courses"]) == 0:
            errors.append("추출된 강의가 없습니다")

        # 각 강의별 검증
        for i, course in enumerate(data["courses"]):
            # 필수 필드 확인
            if not course.get("course_id"):
                errors.append(f"강의 #{i+1}: course_id 누락")

            # 음수 값 확인
            if course.get("revenue", 0) < 0:
                warnings.append(f"강의 {course.get('course_id')}: 매출액이 음수입니다")

    # 3. 합계 검증
    if "courses" in data and "total_revenue" in data:
        calculated_revenue = sum(c.get("revenue", 0) for c in data["courses"])
        diff = abs(calculated_revenue - data["total_revenue"])
        if diff > 1.0:  # 1원 이상 차이
            warnings.append(
                f"매출 합계 불일치: 계산값 {calculated_revenue:,.0f} != "
                f"기록값 {data['total_revenue']:,.0f} (차이: {diff:,.0f}원)"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ─────────────────────────────────────────────────────────
# CLI 테스트용 메인
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python pdf_extractor.py <PDF 파일 경로>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    base_path = str(Path(__file__).parent.parent.parent)

    print(f"📄 PDF 추출 시작: {pdf_path}")
    print()

    try:
        # 추출
        data = extract_pdf_data(pdf_path, base_path)

        # 검증
        validation = validate_extraction(data)

        if validation["errors"]:
            print("❌ 추출 검증 실패:")
            for error in validation["errors"]:
                print(f"  - {error}")
            sys.exit(1)

        if validation["warnings"]:
            print("⚠️  경고:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")
            print()

        # 결과 출력
        print("✅ 추출 완료")
        print(f"   기간: {data['period']}")
        print(f"   강의 수: {data['course_count']}")
        print(f"   총 매출: {data['total_revenue']:,.0f}원")
        print(f"   총 광고비: {data['total_ad_cost']:,.0f}원")
        print()

        # 강의 목록 샘플 (처음 5개)
        print("강의 목록 (샘플):")
        for course in data["courses"][:5]:
            print(f"  - {course['course_id']}: {course['course_name'][:30]:30} "
                  f"매출 {course['revenue']:>10,.0f}원")

        # JSON 저장
        output_path = f"output/{data['period']}/intermediate_data.json"
        save_extracted_data(data, output_path)

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
