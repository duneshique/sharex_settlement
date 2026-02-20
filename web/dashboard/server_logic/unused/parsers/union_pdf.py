"""
Union 정산서 PDF 파서
==============================
기업별 정산서 PDF에서 정산 금액을 추출합니다 (검증 참조용).

Union 정산서 구조 (page 1):
- 총 매출액, 광고비, 공헌이익, 수익쉐어 강사료 (요약)
- [B2C] 월별 상세 (정산월, 강좌명, 매출액, 마케팅비용, 공헌이익, 수익쉐어 강사료)
- 수익쉐어 강사료 = 공헌이익 * 50%

Union 광고비 사용내역 PDF 구조 (page 2 또는 별도 파일):
- 광고비 산출내역: 기간, 광고구분, 총 광고비 A, 전체 강의 수 B, 강의 수 C, 광고비
- 매체별/캠페인별 세부내역
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber

from .base import clean_numeric


def parse_union_settlement_pdf(pdf_path: str) -> Dict:
    """
    Union 정산서 PDF에서 정산 요약 추출

    Returns:
        {
            "company_name": str,
            "total_revenue": float,
            "total_ad_cost": float,
            "contribution_margin": float,
            "settlement_amount": float,  # 수익쉐어 강사료
            "period": str,
        }
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""

    result = {
        "source": str(pdf_path),
        "company_name": "",
        "total_revenue": 0.0,
        "total_ad_cost": 0.0,
        "contribution_margin": 0.0,
        "settlement_amount": 0.0,
        "period": "",
    }

    # 기업명 추출: [ 기업명 ] 형태 (날짜 제외)
    matches = re.findall(r'\[\s*([^\]]+?)\s*\]', text)
    for m in matches:
        m = m.strip()
        # 숫자로만 이루어지거나 날짜 형식([2025.01.26])인 것 제외
        if not re.match(r'^[\d.\-\s]+$', m):
            result["company_name"] = m
            break

    # 기간 추출
    period_match = re.search(r'(\d{4})\s*년\s*(\d)\s*분기', text)
    if period_match:
        result["period"] = f"{period_match.group(1)}-Q{period_match.group(2)}"

    # 요약 테이블에서 수치 추출
    # "총 매출액  광고비  공헌이익  수익쉐어 강사료"
    # "18,315,870  1,018,420  17,297,450  8,648,730"

    # 수익쉐어 강사료 (가장 확실한 값)
    fee_match = re.search(r'수익쉐어\s*강사료\s*\n?\s*([\d,]+)', text)
    if fee_match:
        result["settlement_amount"] = clean_numeric(fee_match.group(1)) or 0.0

    # 합계 행에서 추출
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if '합계' in line:
            # 다음에 나오는 숫자들 추출
            nums = re.findall(r'[\d,]+', line)
            cleaned = [clean_numeric(n) for n in nums if clean_numeric(n) and clean_numeric(n) > 100]
            if len(cleaned) >= 3:
                result["total_revenue"] = cleaned[0]
                result["total_ad_cost"] = cleaned[1]
                result["contribution_margin"] = cleaned[2]
                if len(cleaned) >= 4:
                    result["settlement_amount"] = cleaned[3]
                break

    return result


def parse_union_ad_detail_pdf(pdf_path: str) -> Dict:
    """
    Union 광고비 사용내역 PDF 파싱

    Returns:
        {
            "company_name": str,
            "course_count": int,
            "monthly_breakdown": [
                {"month": str, "total_ad": float, "total_courses": int,
                 "company_courses": int, "apportioned_ad": float}
            ],
            "total_apportioned_ad": float,
        }
    """
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    result = {
        "source": str(pdf_path),
        "company_name": "",
        "course_count": 0,
        "monthly_breakdown": [],
        "total_apportioned_ad": 0.0,
    }

    # 기업명
    company_match = re.search(r'기업\s*명\s*(\S+)', full_text)
    if company_match:
        result["company_name"] = company_match.group(1)

    # 강의 수
    course_match = re.search(r'강의\s*수\s*(\d+)', full_text)
    if course_match:
        result["course_count"] = int(course_match.group(1))

    # 월별 광고비 산출내역
    # 패턴: "2024.10  [Share X] 통합 광고  ₩5,086,832  38개  2개  267,728"
    monthly_pattern = re.compile(
        r'(20\d{2})[.\-](\d{1,2})\s+.*?[₩\\]?([\d,]+)\s+(\d+)개?\s+(\d+)개?\s+([\d,]+)'
    )
    for match in monthly_pattern.finditer(full_text):
        month_str = f"{match.group(1)}-{int(match.group(2)):02d}"
        total_ad = clean_numeric(match.group(3)) or 0.0
        total_courses = int(match.group(4))
        company_courses = int(match.group(5))
        apportioned = clean_numeric(match.group(6)) or 0.0

        result["monthly_breakdown"].append({
            "month": month_str,
            "total_ad": total_ad,
            "total_courses": total_courses,
            "company_courses": company_courses,
            "apportioned_ad": apportioned,
        })

    # 합계
    if result["monthly_breakdown"]:
        result["total_apportioned_ad"] = sum(
            m["apportioned_ad"] for m in result["monthly_breakdown"]
        )

    return result


def scan_union_settlement_pdfs(
    base_dir: str,
    period_filter: str = "",
) -> Dict[str, Dict]:
    """
    Union_Settlement 디렉토리에서 모든 정산서 PDF를 스캔하고 파싱

    Args:
        base_dir: Union_Settlement 디렉토리 경로
        period_filter: 기간 필터 (예: "4Q", "2024")

    Returns:
        {company_name: settlement_data}
    """
    base = Path(base_dir)
    results = {}

    # 루트 레벨 정산서 PDF
    for pdf in base.glob("*.pdf"):
        if "정산서" in pdf.name and (not period_filter or period_filter in pdf.name):
            data = parse_union_settlement_pdf(str(pdf))
            if data["company_name"]:
                results[data["company_name"]] = data

    # 기업별 폴더의 광고비 사용내역 PDF
    for folder in base.iterdir():
        if not folder.is_dir() or folder.name.startswith("."):
            continue

        for pdf in folder.glob("*.pdf"):
            if "광고비" in pdf.name and (not period_filter or period_filter in pdf.name):
                ad_data = parse_union_ad_detail_pdf(str(pdf))
                company = ad_data.get("company_name", folder.name.split("_")[-1])
                if company in results:
                    results[company]["ad_detail"] = ad_data
                else:
                    results[company] = {"ad_detail": ad_data}

    return results
