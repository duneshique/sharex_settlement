"""
정산 파이프라인
==============================
파서 → 안분 계산 엔진 → 교차검증

두 가지 경로:
1. quarterly_pdf: 분기 정산서 PDF에서 확정 데이터 직접 추출 → 유니온 지급액 계산
2. monthly: 월별 PDF/Excel에서 매출+광고비 추출 → 엔진으로 안분 계산

Args:
    period: 정산 기간 (예: "2024-Q4")
    source: "pdf", "excel", "quarterly_pdf"
    base_path: 프로젝트 루트 경로
"""

import json
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

from .apportionment import (
    ApportionmentEngine,
    CampaignCost,
    CompanySettlement,
    CourseSales,
    ValidationResult,
    parse_quarter_months,
)
from .parsers.base import (
    CourseSettlementRow,
    ParsedSettlementData,
    load_course_mapping,
)
from .parsers.fastcampus_pdf import (
    parse_quarterly_pdf,
    parse_monthly_pdf,
    detect_period_from_filename,
)
from .parsers.excel_settlement import (
    parse_master_settlement_sheet,
    parse_info_campaign_data,
    parse_info_raw_data,
)


# ──────────────────────────────────────────────
# Q4 2024 확정 금액 (검증 기준)
# ──────────────────────────────────────────────

EXPECTED_Q4_2024 = {
    "huskyfox": 6432849.5,
    "cosmicray": 4083126.5,
    "bkid": 4509514.5,
    "heaz": 3659120.0,
    "atelier_dongga": 2392750.5,
    "fontrix": 949759.0,
    "dfy": 2994788.5,
    "compound_c": 2255400.0,
    "csidecity": 1930270.5,
    "blsn": 1031299.0,
    "sandoll": 2469468.5,
}
EXPECTED_Q4_2024_TOTAL = 32708346.5


def run_quarterly_pdf_pipeline(
    base_path: str,
    period: str = "2024-Q4",
) -> Dict[str, float]:
    """
    분기 정산서 PDF에서 직접 유니온 지급액 계산

    Q4 PDF의 유니온 섹션에서 강의별 공헌이익을 추출하고,
    기업별로 합산한 뒤 × 0.5를 적용하여 유니온 실지급액 계산.

    Returns:
        {company_id: union_payout}
    """
    print(f"\n{'='*60}")
    print(f"분기 정산서 PDF 파이프라인: {period}")
    print(f"{'='*60}")

    # 분기 PDF 파일 찾기
    fc_dir = Path(base_path) / "FastCampus_Settlement"
    quarterly_pdf = _find_quarterly_pdf(fc_dir, period)
    if not quarterly_pdf:
        print(f"[Error] {period} 분기 정산서 PDF를 찾을 수 없습니다.")
        return {}

    print(f"[PDF] {quarterly_pdf.name}")

    # PDF 파싱
    data = parse_quarterly_pdf(str(quarterly_pdf), period, base_path)

    if not data.settlement_rows:
        print("[Error] 정산 데이터를 추출할 수 없습니다.")
        return {}

    print(f"[파싱] {len(data.settlement_rows)}개 강의 추출")

    # 유니온 섹션만 필터
    union_rows = [r for r in data.settlement_rows if r.section == "union"]
    plusx_rows = [r for r in data.settlement_rows if r.section == "plusx"]

    print(f"  Plus X: {len(plusx_rows)}개 강의")
    print(f"  Union:  {len(union_rows)}개 강의")

    if not union_rows:
        print("[Warning] 유니온 섹션 데이터가 없습니다. 전체 데이터에서 매핑으로 분류합니다.")
        union_rows = _classify_rows_by_mapping(data.settlement_rows, base_path)

    # 기업별 공헌이익 합산
    mapping = load_course_mapping(base_path)
    company_margins: Dict[str, float] = {}

    for row in union_rows:
        company_id = mapping.get(row.course_id, {}).get("company_id")
        if not company_id or company_id == "plusx":
            continue

        company_margins[company_id] = company_margins.get(company_id, 0) + row.contribution_margin

    # 유니온 실지급 = 공헌이익 × 50%
    union_payouts = {
        cid: margin * 0.5
        for cid, margin in company_margins.items()
    }

    # 결과 출력
    print(f"\n[기업별 유니온 실지급]")
    print(f"{'기업ID':<20} {'공헌이익':>15} {'유니온 실지급':>15}")
    print("-" * 50)

    total = 0.0
    for cid in sorted(union_payouts.keys(), key=lambda x: union_payouts[x], reverse=True):
        margin = company_margins[cid]
        payout = union_payouts[cid]
        total += payout
        print(f"{cid:<20} {margin:>15,.0f} {payout:>15,.1f}")

    print("-" * 50)
    print(f"{'합계':<20} {'':>15} {total:>15,.1f}")

    return union_payouts


def run_monthly_pipeline(
    base_path: str,
    period: str = "2024-Q4",
    source: str = "pdf",
) -> Dict[str, CompanySettlement]:
    """
    월별 데이터에서 안분 계산 엔진을 통해 정산 수행

    Args:
        base_path: 프로젝트 루트
        period: 정산 기간 (예: "2024-Q4")
        source: "pdf" (FastCampus 월별 PDF) 또는 "excel" (Master/Info Excel)

    Returns:
        {company_id: CompanySettlement}
    """
    print(f"\n{'='*60}")
    print(f"월별 파이프라인: {period} (소스: {source})")
    print(f"{'='*60}")

    months = parse_quarter_months(period)
    engine = ApportionmentEngine(base_path)
    engine.load_config()

    if source == "pdf":
        _load_from_monthly_pdfs(engine, base_path, months)
    elif source == "excel":
        _load_from_excel(engine, base_path, months)
    else:
        raise ValueError(f"Unknown source: {source}")

    print(f"\n[데이터 로드 완료]")
    print(f"  매출 데이터: {len(engine.course_sales)}건")
    print(f"  광고비 데이터: {len(engine.campaign_costs)}건")

    # 안분 계산
    # 각 기업의 revenue_share_ratio, union_payout_ratio를 companies.json에서 로드
    # (None 전달 시 엔진이 각 기업별 설정값 사용)
    results = engine.calculate_settlement(
        period=period,
        period_months=months,
        revenue_share_ratio=None,  # companies.json의 기업별 설정 사용
        union_payout_ratio=None,   # companies.json의 기업별 설정 사용
    )

    return results


def validate_results(
    results: Dict[str, float],
    expected: Dict[str, float] = None,
    tolerance: float = 1.0,
) -> bool:
    """
    계산 결과를 확정 금액과 비교 검증

    Args:
        results: {company_id: union_payout}
        expected: {company_id: expected_amount} (기본: Q4 2024)
        tolerance: 허용 오차 (원)

    Returns:
        True if all checks pass
    """
    if expected is None:
        expected = EXPECTED_Q4_2024

    print(f"\n{'='*60}")
    print(f"교차검증 결과")
    print(f"{'='*60}")
    print(f"{'기업ID':<20} {'예상':>15} {'실제':>15} {'차이':>10} {'결과':>6}")
    print("-" * 70)

    all_passed = True
    total_expected = 0.0
    total_actual = 0.0

    for cid in sorted(expected.keys()):
        exp = expected[cid]
        act = results.get(cid, 0.0)
        diff = abs(act - exp)
        passed = diff <= tolerance

        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False

        total_expected += exp
        total_actual += act

        print(f"{cid:<20} {exp:>15,.1f} {act:>15,.1f} {diff:>10,.1f} {status:>6}")

    # 합계
    total_diff = abs(total_actual - total_expected)
    total_passed = total_diff <= tolerance * len(expected)

    print("-" * 70)
    print(f"{'합계':<20} {total_expected:>15,.1f} {total_actual:>15,.1f} {total_diff:>10,.1f} {'PASS' if total_passed else 'FAIL':>6}")
    print(f"\n{'ALL PASS' if all_passed else 'SOME FAILED'}")

    # 누락/초과 기업 체크
    missing = set(expected.keys()) - set(results.keys())
    extra = set(results.keys()) - set(expected.keys())
    if missing:
        print(f"\n[Warning] 누락 기업: {missing}")
    if extra:
        print(f"[Info] 추가 기업 (예상 외): {extra}")

    return all_passed


# ──────────────────────────────────────────────
# 내부 헬퍼 함수
# ──────────────────────────────────────────────

def _find_quarterly_pdf(fc_dir: Path, period: str) -> Optional[Path]:
    """분기 정산서 PDF 파일 찾기"""
    year = period.split("-Q")[0]
    quarter = period.split("-Q")[1]

    for pdf in fc_dir.glob("*.pdf"):
        # macOS NFD Unicode normalization for Korean filenames
        name = unicodedata.normalize("NFC", pdf.name)
        if year in name and (f"{quarter}Q" in name or f"{quarter}분기" in name):
            return pdf

    return None


def _find_monthly_pdfs(fc_dir: Path, months: List[str]) -> Dict[str, Path]:
    """월별 정산서 PDF 파일 찾기"""
    result = {}
    for pdf in fc_dir.glob("*.pdf"):
        period_type, value = detect_period_from_filename(pdf.name)
        if period_type == "monthly" and value in months:
            result[value] = pdf
    return result


def _load_from_monthly_pdfs(
    engine: ApportionmentEngine,
    base_path: str,
    months: List[str],
) -> None:
    """월별 FastCampus PDF에서 데이터 로드"""
    fc_dir = Path(base_path) / "FastCampus_Settlement"
    monthly_pdfs = _find_monthly_pdfs(fc_dir, months)

    for month, pdf_path in sorted(monthly_pdfs.items()):
        print(f"\n[파싱] {pdf_path.name}")
        data = parse_monthly_pdf(str(pdf_path), month, base_path)

        for sales in data.course_sales:
            engine.add_course_sales(CourseSales(
                month=sales.month,
                course_id=sales.course_id,
                course_name=sales.course_name,
                company_id=sales.company_id,
                revenue=sales.revenue,
            ))

        for cost in data.campaign_costs:
            # Meta USD → KRW 환율 변환
            cost_krw = cost.cost_krw
            exchange_rate = cost.exchange_rate

            if cost.cost_usd > 0 and cost_krw == 0:
                # Meta 광고비 (USD only) → engine의 환율로 변환
                cost_krw = engine.convert_usd_to_krw(cost.cost_usd, cost.month)
                exchange_rate = engine.exchange_rates.get(cost.month, 0.0)

            engine.add_campaign_cost(CampaignCost(
                month=cost.month,
                channel=cost.channel,
                target=cost.target,
                campaign_name=cost.campaign_name,
                cost_krw=cost_krw,
                cost_usd=cost.cost_usd,
                exchange_rate=exchange_rate,
            ))

    # 누락 월 확인
    missing = set(months) - set(monthly_pdfs.keys())
    if missing:
        print(f"\n[Warning] 누락 월: {missing}")


def _load_from_excel(
    engine: ApportionmentEngine,
    base_path: str,
    months: List[str],
) -> None:
    """Excel Master/Info 파일에서 데이터 로드"""
    master_path = Path(base_path) / "Share X Settlement_Master_2023-2026.xlsx"
    info_path = Path(base_path) / "Share X Settlement_Info.xlsx"

    # 1. Master 파일에서 월별 매출 데이터
    if master_path.exists():
        for month in months:
            year_short = month[2:4]
            month_num = month[5:7]
            sheet_name = f"{year_short}.{month_num}_정산(실비)"

            print(f"\n[Excel] {sheet_name}")
            sales = parse_master_settlement_sheet(
                str(master_path), sheet_name, month, base_path
            )
            for s in sales:
                engine.add_course_sales(CourseSales(
                    month=s.month,
                    course_id=s.course_id,
                    course_name=s.course_name,
                    company_id=s.company_id,
                    revenue=s.revenue,
                ))

    # 2. Info 파일에서 광고비 데이터
    if info_path.exists():
        print(f"\n[Excel] 광고비 데이터 파싱 (Info)")
        costs = parse_info_campaign_data(str(info_path), months, base_path)
        for c in costs:
            # Meta USD → KRW 환율 변환
            cost_krw = c.cost_krw
            exchange_rate = c.exchange_rate

            if c.cost_usd > 0 and cost_krw == 0:
                # Meta 광고비 (USD only) → engine의 환율로 변환
                cost_krw = engine.convert_usd_to_krw(c.cost_usd, c.month)
                exchange_rate = engine.exchange_rates.get(c.month, 0.0)

            engine.add_campaign_cost(CampaignCost(
                month=c.month,
                channel=c.channel,
                target=c.target,
                campaign_name=c.campaign_name,
                cost_krw=cost_krw,
                cost_usd=c.cost_usd,
                exchange_rate=exchange_rate,
            ))


def _classify_rows_by_mapping(
    rows: List[CourseSettlementRow],
    base_path: str,
) -> List[CourseSettlementRow]:
    """course_mapping을 사용해 유니온 강의 분류"""
    mapping = load_course_mapping(base_path)
    union_rows = []
    for row in rows:
        course = mapping.get(row.course_id, {})
        company_id = course.get("company_id", "")
        if company_id and company_id != "plusx":
            row.section = "union"
            row.rs_ratio = 0.75
            union_rows.append(row)
    return union_rows
