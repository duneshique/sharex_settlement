"""
FastCampus 정산서 PDF 파서
==============================
패스트캠퍼스에서 발행하는 정산서 PDF를 파싱합니다.

두 가지 유형:
1. 월별 정산서: 강의별 매출, 직접/간접 광고비, 공헌이익, 강사료 + Meta/Google/Naver 인보이스
2. 분기 정산서: 강의별 분기 합산 매출, 광고비, 공헌이익, 강사료 (확정)
"""

import re
import unicodedata
from pathlib import Path
from typing import List, Optional, Tuple

import pdfplumber

from server_logic.parsers.base import (
    CampaignCost,
    CourseSales,
    CourseSettlementRow,
    ParsedSettlementData,
    clean_numeric,
    load_course_mapping,
    get_course_company_id,
)


def parse_quarterly_pdf(pdf_path: str, period: str, base_path: str) -> ParsedSettlementData:
    """
    분기 정산서 PDF 파싱 (예: "[패스트캠퍼스] Share X 정산서 - 2024년 4Q.pdf")

    분기 정산서는 1페이지에 Plus X 섹션과 Union 섹션이 있으며,
    각 섹션별로 강의별 {매출액, 광고비, 공헌이익, 수익쉐어 강사료}를 포함합니다.

    Args:
        pdf_path: PDF 파일 경로
        period: 정산 기간 (예: "2024-Q4")
        base_path: 프로젝트 루트 경로 (course_mapping 로드용)

    Returns:
        ParsedSettlementData (settlement_rows 포함)
    """
    mapping = load_course_mapping(base_path)
    result = ParsedSettlementData(metadata={
        "source": pdf_path,
        "period": period,
        "type": "quarterly",
    })

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""

    # pdfplumber 테이블 추출이 이 PDF에서 불안정하므로,
    # 텍스트 기반 파싱을 사용
    result.settlement_rows = _parse_quarterly_from_text(text, period, mapping)

    return result


def _parse_quarterly_table(
    table: list, period: str, mapping: dict
) -> List[CourseSettlementRow]:
    """분기 정산서 테이블 파싱"""
    rows = []
    current_section = "unknown"
    current_ratio = 0.0

    for row in table:
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        # 첫 번째 셀에서 섹션 식별
        first_cell = str(row[0] or "").strip()
        row_text = " ".join(str(c or "") for c in row)

        # 섹션 감지
        if "유니온" in row_text:
            current_section = "union"
            current_ratio = 0.75
            continue
        elif "플러스엑스" in row_text and "유니온" not in row_text:
            if "정산" in row_text or "내역" in row_text:
                current_section = "plusx"
                current_ratio = 0.70
                continue

        # R/S 비율 감지
        if "70%" in row_text:
            current_ratio = 0.70
        elif "75%" in row_text:
            current_ratio = 0.75

        # 헤더 행 스킵
        if "코스아이디" in row_text or "정산월" in row_text or "강의명" in row_text:
            continue

        # 합계 행 스킵
        if "합계" in row_text:
            continue

        # 계약조건 행 스킵
        if "계약" in row_text or "마케팅" in row_text or "R/S" in row_text:
            continue

        # 데이터 행 파싱 - 코스아이디 찾기
        course_id = _find_course_id(row)
        if not course_id:
            continue

        # 숫자 컬럼 추출 (매출액, 광고비, 공헌이익, 강사료)
        nums = _extract_numeric_columns(row)
        if len(nums) < 4:
            continue

        revenue = nums[0]
        ad_cost = nums[1]
        contribution = nums[2]
        rs_fee = nums[3]

        # "-" 값 처리 (235522 허스키폭스 어플리케이션 등)
        if revenue is None and ad_cost is None:
            revenue = 0.0
            ad_cost = 0.0
            contribution = 0.0
            rs_fee = 0.0

        course_name = _find_course_name(row)

        settlement_row = CourseSettlementRow(
            period=period,
            course_id=course_id,
            course_name=course_name,
            revenue=revenue or 0.0,
            ad_cost=ad_cost or 0.0,
            contribution_margin=contribution or 0.0,
            revenue_share_fee=rs_fee or 0.0,
            section=current_section,
            rs_ratio=current_ratio,
        )
        rows.append(settlement_row)

    return rows


def _parse_quarterly_from_text(
    text: str, period: str, mapping: dict
) -> List[CourseSettlementRow]:
    """
    텍스트 기반으로 분기 정산서 파싱

    pdfplumber 텍스트 추출 시 긴 강의명의 숫자가 텍스트에 섞이는 문제가 있음.
    해결: 라인 끝에서부터 공백으로 구분된 숫자들을 역순으로 추출.
    마지막 3개 숫자가 항상 깨끗함 (광고비, 공헌이익, 강사료).
    """
    rows = []
    lines = text.split("\n")
    current_section = "unknown"
    current_ratio = 0.0

    for line in lines:
        line = line.strip()

        # 섹션 감지
        if "유니온" in line and ("정산" in line or "내역" in line):
            current_section = "union"
            current_ratio = 0.75
            continue
        elif "플러스엑스" in line and "유니온" not in line:
            if "정산" in line or "내역" in line:
                current_section = "plusx"
                current_ratio = 0.70
                continue

        # R/S 비율 감지
        if "R/S" in line and "70%" in line:
            current_ratio = 0.70
        elif "R/S" in line and "75%" in line:
            current_ratio = 0.75

        # 코스 ID가 포함된 행 찾기 (21xxxx ~ 24xxxx)
        course_match = re.search(r'\b(2[1-4]\d{4})\b', line)
        if not course_match:
            continue

        # 합계/헤더 행 스킵
        if "합계" in line or "코스아이디" in line:
            continue

        course_id = course_match.group(1)

        # "-" 전용 행 (235522 허스키폭스 어플리케이션: "- - - -")
        trailing = line[line.rfind(course_id) + len(course_id):]
        if re.search(r'-\s+-\s+-\s+-', trailing):
            rows.append(CourseSettlementRow(
                period=period,
                course_id=course_id,
                course_name="",
                revenue=0.0,
                ad_cost=0.0,
                contribution_margin=0.0,
                revenue_share_fee=0.0,
                section=current_section,
                rs_ratio=current_ratio,
            ))
            continue

        # 끝에서부터 공백 구분 숫자 토큰 추출
        # 패턴: "1,377,321" 또는 "150" 형태
        nums_from_right = _extract_numbers_from_right(line)

        if len(nums_from_right) < 3:
            continue

        # 마지막 4개 숫자: 매출액, 광고비, 공헌이익, 강사료
        # 단, 매출액이 텍스트에 섞여 3개만 깨끗할 수 있음
        if len(nums_from_right) >= 4:
            revenue = nums_from_right[-4]
            ad_cost = nums_from_right[-3]
            contribution = nums_from_right[-2]
            rs_fee = nums_from_right[-1]
        else:
            # 3개만 있으면: 광고비, 공헌이익, 강사료
            revenue = 0.0  # 매출액은 공헌이익 + 광고비로 역산
            ad_cost = nums_from_right[-3]
            contribution = nums_from_right[-2]
            rs_fee = nums_from_right[-1]
            revenue = contribution + ad_cost  # 역산

        rows.append(CourseSettlementRow(
            period=period,
            course_id=course_id,
            course_name="",
            revenue=revenue,
            ad_cost=ad_cost,
            contribution_margin=contribution,
            revenue_share_fee=rs_fee,
            section=current_section,
            rs_ratio=current_ratio,
        ))

    # 강의명 보충 (course_mapping에서)
    for row in rows:
        course = mapping.get(row.course_id, {})
        if course:
            row.course_name = course.get("course_name", "")

    # 매출액 검증/보정: pdfplumber가 강의명과 숫자를 섞어 추출하는 경우 대응
    # (예: "경6험,9 설65계,000" → revenue=0으로 잘못 추출)
    for row in rows:
        expected_revenue = row.contribution_margin + row.ad_cost
        if row.contribution_margin > 0 and abs(row.revenue - expected_revenue) > 1.0:
            print(f"  ℹ️  매출액 보정: {row.course_id} {row.course_name[:30]}... "
                  f"{row.revenue:,.0f} → {expected_revenue:,.0f}원 (공헌이익+광고비 역산)")
            row.revenue = expected_revenue

    return rows


def _extract_numbers_from_right(line: str) -> List[float]:
    """
    라인 끝에서부터 공백으로 구분된 comma-formatted 숫자들을 추출.

    PDF 텍스트에서 강의명과 첫 번째 숫자가 붙는 문제를 해결.
    끝에서부터 역순으로 추출하면 항상 깨끗한 숫자를 얻을 수 있음.
    """
    # 라인을 공백으로 분리
    tokens = line.split()
    nums = []

    # 뒤에서부터 숫자 토큰 추출
    for token in reversed(tokens):
        # 순수 comma-formatted 숫자 패턴: "1,377,321" 또는 "150" 또는 "1,400"
        if re.match(r'^[\d,]+$', token):
            val = clean_numeric(token)
            if val is not None:
                nums.insert(0, val)
        else:
            # 숫자가 아닌 토큰을 만나면 중단
            # 단, 텍스트와 숫자가 붙어있을 수 있음 (예: "실무10,396,350")
            # 끝에 붙은 숫자 추출 시도
            tail_match = re.search(r'([\d,]{3,})$', token)
            if tail_match:
                val = clean_numeric(tail_match.group(1))
                if val is not None:
                    nums.insert(0, val)
            # 더 이상 역추출 중단
            break

    return nums


def parse_monthly_pdf(pdf_path: str, month: str, base_path: str) -> ParsedSettlementData:
    """
    월별 정산서 PDF 파싱 (예: "[패스트캠퍼스] Share X 정산서 - 2024년 10월.pdf")

    Page 1: 정산 테이블 (매출, 직접광고비, 간접광고비, 공헌이익, 강사료)
    Page 3+: Meta 인보이스 (캠페인별 USD 금액)
    Page 4+: Google 인보이스 (KRW)
    Page 5+: Naver 세금계산서 (KRW)

    Args:
        pdf_path: PDF 파일 경로
        month: 정산월 (예: "2024-10")
        base_path: 프로젝트 루트

    Returns:
        ParsedSettlementData (course_sales + campaign_costs + settlement_rows)
    """
    mapping = load_course_mapping(base_path)
    result = ParsedSettlementData(metadata={
        "source": pdf_path,
        "month": month,
        "type": "monthly",
    })

    with pdfplumber.open(pdf_path) as pdf:
        # Page 1: 정산 테이블
        if len(pdf.pages) > 0:
            page1_text = pdf.pages[0].extract_text() or ""
            result.course_sales = _parse_monthly_sales(page1_text, month, mapping)
            # 정산 행도 생성 (전체 컬럼: 매출액, 직접광고비, 간접광고비)
            result.settlement_rows = _parse_monthly_settlement_rows(page1_text, month, mapping)

            # 텍스트 노트에서 인보이스 총액 추출
            invoice_totals = _extract_invoice_totals(page1_text, month)
            result.campaign_costs.extend(invoice_totals)

        # Page 3: Meta 인보이스
        for page in pdf.pages[1:]:
            page_text = page.extract_text() or ""
            if "Meta" in page_text or "Facebook" in page_text or "INVOICE" in page_text:
                meta_costs = _parse_meta_invoice(page_text, month)
                if meta_costs:
                    result.campaign_costs.extend(meta_costs)
                    # 인보이스에서 가져온 상세 데이터가 있으면, 총액 기반 데이터 대체
                    result.campaign_costs = _deduplicate_costs(result.campaign_costs, "Meta")

    return result


def _parse_monthly_sales(
    text: str, month: str, mapping: dict
) -> List[CourseSales]:
    """
    월별 정산서 Page 1에서 매출 데이터 추출

    라인 형식:
        YYYY년 MM월 COURSE_ID [쉐어엑스]강의명... 매출액 직접광고비 간접광고비 [공헌이익 강사료]
    매출액 = 코스ID 이후 첫 번째 순수 숫자 토큰
    """
    sales = []
    lines = text.split("\n")

    for line in lines:
        # 코스ID 패턴 찾기
        course_match = re.search(r'\b(2[1-4]\d{4})\b', line)
        if not course_match:
            continue

        if "합계" in line or "코스아이디" in line:
            continue

        course_id = course_match.group(1)
        company_id = get_course_company_id(course_id, mapping) or "unknown"

        # 코스ID 이후 텍스트에서 숫자 추출
        ci_pos = line.find(course_id)
        after_id = line[ci_pos + len(course_id):]

        # 토큰을 순회하며 첫 번째 순수 숫자 토큰 = 매출액
        revenue = None
        tokens = after_id.split()
        for t in tokens:
            # 순수 숫자 토큰만 (콤마 포함, 부호 포함)
            if re.match(r'^-?[\d,]+$', t):
                val = clean_numeric(t)
                if val is not None:
                    revenue = val
                    break

        if revenue is None:
            continue

        course_name = mapping.get(course_id, {}).get("course_name", "")

        sales.append(CourseSales(
            month=month,
            course_id=course_id,
            course_name=course_name,
            company_id=company_id,
            revenue=revenue,
        ))

    return sales


def _parse_monthly_settlement_rows(
    text: str, month: str, mapping: dict
) -> List[CourseSettlementRow]:
    """
    월별 정산서에서 정산 행 추출 (매출액 + 직접광고비 + 간접광고비)

    월별 PDF 컬럼: 매출액, 직접 광고비, 간접광고비, [공헌이익, 강사료는 섹션 합계에만]
    → 강의별 공헌이익 = 매출액 - 직접광고비 - 간접광고비
    → 강사료 = 공헌이익 × R/S 비율 (플러스엑스 70%, 유니온 75%)
    """
    rows = []
    lines = text.split("\n")
    current_section = "unknown"
    current_ratio = 0.0

    for line in lines:
        line_stripped = line.strip()

        # 섹션 감지: "[플러스엑스]" 또는 "[유니온]" 헤더
        if "[플러스엑스]" in line_stripped and "단위" in line_stripped:
            current_section = "plusx"
            current_ratio = 0.70
            continue
        elif "[유니온]" in line_stripped and "단위" in line_stripped:
            current_section = "union"
            current_ratio = 0.75
            continue

        # R/S 비율 감지 (헤더에 70% 또는 75% 포함)
        if "70%" in line_stripped and ("수익쉐어" in line_stripped or "강사료" in line_stripped):
            current_ratio = 0.70
        elif "75%" in line_stripped and ("수익쉐어" in line_stripped or "강사료" in line_stripped):
            current_ratio = 0.75

        # 코스ID 패턴 찾기
        course_match = re.search(r'\b(2[1-4]\d{4})\b', line_stripped)
        if not course_match:
            continue

        if "합계" in line_stripped or "코스아이디" in line_stripped:
            continue

        course_id = course_match.group(1)

        # 끝에서부터 숫자 추출
        nums = _extract_numbers_from_right(line_stripped)

        if len(nums) < 3:
            continue

        # 월별 PDF는 뒤에서부터: ..., 간접광고비, 직접광고비, 매출액 (3개 이상)
        # 섹션 합계가 마지막 행에 붙는 경우 5개 이상일 수 있음
        if len(nums) >= 5:
            # 마지막 2개는 섹션 합계 (공헌이익, 강사료) → 무시
            indirect_ad = nums[-3]
            direct_ad = nums[-4]
            revenue = nums[-5]
        elif len(nums) >= 3:
            indirect_ad = nums[-1]
            direct_ad = nums[-2]
            revenue = nums[-3]
        else:
            continue

        ad_cost = direct_ad + indirect_ad
        contribution = revenue - ad_cost
        rs_fee = contribution * current_ratio

        course_name = mapping.get(course_id, {}).get("course_name", "")

        rows.append(CourseSettlementRow(
            period=month,
            course_id=course_id,
            course_name=course_name,
            revenue=revenue,
            ad_cost=ad_cost,
            contribution_margin=contribution,
            revenue_share_fee=round(rs_fee, 2),
            section=current_section,
            rs_ratio=current_ratio,
        ))

    # 매출액 검증/보정 (분기 파서와 동일)
    for row in rows:
        expected_revenue = row.contribution_margin + row.ad_cost
        if row.contribution_margin > 0 and abs(row.revenue - expected_revenue) > 1.0:
            print(f"  ℹ️  월별 매출액 보정: {row.course_id} {row.course_name[:30]}... "
                  f"{row.revenue:,.0f} → {expected_revenue:,.0f}원")
            row.revenue = expected_revenue

    return rows


def _extract_invoice_totals(text: str, month: str) -> List[CampaignCost]:
    """
    정산서 텍스트 노트에서 인보이스 총액 추출
    예: "메타 : ₩8,028,348 (= $5,898.86 (10월 매매 평균 환율 1361.00))"
    """
    costs = []

    # 메타 총액
    meta_match = re.search(
        r'메타\s*[:：]\s*[₩\\]?([\d,]+)\s*(?:\(.*?\$?([\d,.]+).*?환율\s*([\d,.]+)\))?',
        text
    )
    if meta_match:
        krw = clean_numeric(meta_match.group(1))
        usd = clean_numeric(meta_match.group(2)) if meta_match.group(2) else 0.0
        rate = clean_numeric(meta_match.group(3)) if meta_match.group(3) else 0.0
        if krw:
            costs.append(CampaignCost(
                month=month,
                channel="Meta",
                target="SHARE X",  # 기본값, 상세 분류는 인보이스 파싱에서
                campaign_name="Meta 총액",
                cost_krw=krw,
                cost_usd=usd or 0.0,
                exchange_rate=rate or 0.0,
            ))

    # 구글 총액
    google_match = re.search(r'구글\s*[:：]\s*[₩\\]?([\d,]+)', text)
    if google_match:
        krw = clean_numeric(google_match.group(1))
        if krw:
            costs.append(CampaignCost(
                month=month,
                channel="Google",
                target="SHARE X",
                campaign_name="Google 총액",
                cost_krw=krw,
            ))

    # 네이버 총액
    naver_match = re.search(r'네이버\s*[:：]\s*[₩\\]?([\d,]+)', text)
    if naver_match:
        krw = clean_numeric(naver_match.group(1))
        if krw:
            costs.append(CampaignCost(
                month=month,
                channel="Naver",
                target="SHARE X",
                campaign_name="Naver 총액",
                cost_krw=krw,
            ))

    return costs


def _parse_meta_invoice(text: str, month: str) -> List[CampaignCost]:
    """Meta 인보이스 페이지에서 캠페인별 USD 금액 추출"""
    costs = []

    # 환율 추출 (정산서 page 1에서 이미 추출했을 수 있으나 여기서도 시도)
    # 인보이스에는 환율이 없으므로, config에서 가져와야 함

    # 캠페인별 행 파싱: "Line# Description Campaign Label Total"
    # 예: "1 ASC_쉐어엑스^100008 캠페인 430.30"
    lines = text.split("\n")
    for line in lines:
        # 캠페인 행 패턴: 숫자 + 캠페인명 + 금액
        match = re.match(
            r'\s*(\d+)\s+(.+?)\s+([-\d,]+\.?\d*)\s*$',
            line.strip()
        )
        if not match:
            continue

        line_num = match.group(1)
        description = match.group(2).strip()
        amount_str = match.group(3)

        # Subtotal/Freight/VAT/Total 행 스킵
        if any(kw in description.lower() for kw in ['subtotal', 'freight', 'vat', 'total', 'invoice']):
            continue

        amount_usd = clean_numeric(amount_str)
        if amount_usd is None:
            continue

        # 캠페인명에서 target 분류
        target = _classify_meta_campaign(description)

        costs.append(CampaignCost(
            month=month,
            channel="Meta",
            target=target,
            campaign_name=description,
            cost_krw=0.0,  # 환율 변환 필요
            cost_usd=amount_usd,
        ))

    return costs


def _classify_meta_campaign(campaign_name: str) -> str:
    """Meta 캠페인명에서 광고 대상 분류"""
    name = campaign_name.lower()

    # 직접 광고 키워드
    if "플러스엑스" in name or "plus x" in name or "plusx" in name:
        return "PLUS X"
    if "bkid" in name or "비케이아이디" in name:
        return "BKID"
    if "blsn" in name or "블센" in name:
        return "BLSN"
    if "산돌" in name or "sandoll" in name:
        return "SANDOLL"

    # IP 프로모션 (Career Pass 등) → 플러스엑스 직접
    if "ip 프로모션" in name or "ip_쉐어엑스_전환" in name:
        return "PLUS X"

    # ASC_쉐어엑스 → 통합광고 (간접)
    if "asc" in name or "쉐어엑스" in name:
        return "SHARE X"

    # Coupons/goodwill → 간접으로 처리
    if "coupon" in name or "goodwill" in name:
        return "SHARE X"

    return "SHARE X"


def _find_course_id(row: list) -> Optional[str]:
    """테이블 행에서 코스 ID (6자리 숫자) 찾기"""
    for cell in row:
        if cell is None:
            continue
        s = str(cell).strip()
        match = re.search(r'\b(2\d{5})\b', s)
        if match:
            return match.group(1)
    return None


def _find_course_name(row: list) -> str:
    """테이블 행에서 강의명 찾기"""
    for cell in row:
        if cell is None:
            continue
        s = str(cell).strip()
        if "쉐어엑스" in s or "플러스엑스" in s or "허스키" in s:
            return s
    return ""


def _extract_numeric_columns(row: list) -> List[Optional[float]]:
    """테이블 행에서 숫자 컬럼 추출 (코스ID, 년월 제외)"""
    nums = []
    skip_patterns = re.compile(r'^(2\d{5}|2024|2025|20\d{2})')

    for cell in row:
        if cell is None:
            nums.append(None)
            continue

        s = str(cell).strip()

        # 코스ID나 날짜 패턴은 스킵
        if skip_patterns.match(s.replace(",", "").replace(".", "")):
            continue

        # 강의명 (한글 포함) 스킵
        if re.search(r'[가-힣a-zA-Z]{2,}', s) and not re.match(r'^[\d,.\-₩\\]+$', s):
            continue

        # 숫자 변환 시도
        val = clean_numeric(s)
        if val is not None:
            nums.append(val)
        elif s == "-":
            nums.append(None)

    return nums


def _assign_sections_from_text(
    rows: List[CourseSettlementRow], text: str
) -> None:
    """
    텍스트에서 Plus X / Union 섹션 경계를 찾아 rows에 할당
    """
    # 텍스트에서 유니온 섹션 시작 위치 찾기
    union_pos = text.find("유니온")
    if union_pos < 0:
        return

    # 유니온 섹션 이전 코스ID 목록 추출
    pre_union_text = text[:union_pos]
    plusx_course_ids = set(re.findall(r'\b(2\d{5})\b', pre_union_text))

    for row in rows:
        if row.course_id in plusx_course_ids:
            row.section = "plusx"
            row.rs_ratio = 0.70
        else:
            row.section = "union"
            row.rs_ratio = 0.75


def _deduplicate_costs(
    costs: List[CampaignCost], channel: str
) -> List[CampaignCost]:
    """
    총액 기반 데이터와 상세 데이터가 공존하면, 상세 데이터만 남김
    """
    detailed = [c for c in costs if c.channel == channel and "총액" not in c.campaign_name]
    totals = [c for c in costs if c.channel == channel and "총액" in c.campaign_name]
    others = [c for c in costs if c.channel != channel]

    if detailed:
        return others + detailed
    return others + totals


# ──────────────────────────────────────────────
# 편의 함수: 파일명에서 기간 자동 감지
# ──────────────────────────────────────────────

def detect_period_from_filename(filename: str) -> Tuple[str, str]:
    """
    파일명에서 기간 유형과 값 추출

    Returns:
        (type, value): ("monthly", "2024-10") 또는 ("quarterly", "2024-Q4")
    """
    # macOS uses NFD (decomposed) Unicode for Korean filenames,
    # normalize to NFC so regex literals like '년', '월', '분기' match correctly
    name = unicodedata.normalize("NFC", Path(filename).stem)

    # 분기 패턴: "2024년 4Q" 또는 "2024년 4분기"
    q_match = re.search(r'(\d{4})\s*년\s*(\d)\s*(?:Q|분기)', name)
    if q_match:
        return ("quarterly", f"{q_match.group(1)}-Q{q_match.group(2)}")

    # 월별 패턴: "2024년 10월"
    m_match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월', name)
    if m_match:
        return ("monthly", f"{m_match.group(1)}-{int(m_match.group(2)):02d}")

    return ("unknown", "")
