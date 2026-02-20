"""
통합 PDF 파서 (Unified PDF Parser)
=====================================

ShareX 정산서의 두 가지 양식을 유연하게 처리합니다.

양식 1: 기존 (Excel→PDF) - 2024년 4Q, 2025년 1Q, 2분기, 3분기
- 특징: 1페이지, 텍스트 기반, 코스ID | 강의명 형식
- 컬럼: 매출액, 광고비, 공헌이익, 강사료

양식 2: 새 (HTML 인쇄) - 2025년 4분기, 월별 정산서
- 특징: 다중 페이지, 텍스트 기반, 코스ID_강의명 형식
- 컬럼: 매출액, 프로모션매출액, 제작비, 마케팅비, 계약조건(%), 정산금액
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import unicodedata
from difflib import SequenceMatcher

import pdfplumber

from .base import (
    CourseSettlementRow,
    ParsedSettlementData,
    clean_numeric,
    load_course_mapping,
    get_course_company_id,
    normalize_course_name,
)
from .fastcampus_pdf import parse_quarterly_pdf


def parse_settlement_pdf_unified(
    pdf_path: str,
    period: str,
    base_path: str
) -> ParsedSettlementData:
    """
    통합 파서: 양식을 자동 감지하고 적절한 파서 실행

    Args:
        pdf_path: PDF 파일 경로
        period: 정산 기간 (예: "2024-Q4", "2025-Q4")
        base_path: 프로젝트 루트 경로

    Returns:
        ParsedSettlementData
    """
    format_type = detect_pdf_format(pdf_path)

    if format_type == "excel_format":
        # 기존 파서 사용
        return parse_quarterly_pdf(pdf_path, period, base_path)

    elif format_type == "html_format":
        # 새 양식 파서 사용
        return parse_html_format_pdf(pdf_path, period, base_path)

    else:
        # Fallback: 두 파서 모두 시도
        try:
            result = parse_quarterly_pdf(pdf_path, period, base_path)
            if result.settlement_rows:
                return result
        except Exception as e:
            print(f"기존 파서 실패: {e}")

        try:
            result = parse_html_format_pdf(pdf_path, period, base_path)
            if result.settlement_rows:
                return result
        except Exception as e:
            print(f"새 양식 파서 실패: {e}")

        raise ValueError(f"PDF 양식을 인식할 수 없습니다: {pdf_path}")


def detect_pdf_format(pdf_path: str) -> str:
    """
    PDF 양식 자동 감지

    Returns:
        "excel_format" - 기존 Excel→PDF 양식 (2024-2Q, 2025-1Q, 2Q, 3Q)
        "html_format"  - 새 HTML 인쇄 양식 (2025-4Q, 월별)
        "unknown"      - 인식 불가
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            text = page.extract_text() or ""

            # 방법 1: 파일명에서 양식 추측
            # "2025년 4분기" 또는 "2025년 9월" → 새 양식 가능성
            filename = Path(pdf_path).stem
            if "2025년" in filename and any(
                pattern in filename for pattern in ["4분기", "9월", "10월", "11월", "12월"]
            ):
                # 추가 검증: 텍스트에서 "프로모션 매출액" 또는 "계약조건" 키워드 확인
                if "프로모션" in text or (
                    "매출액" in text and "제작비" in text and "마케팅비" in text
                ):
                    return "html_format"

            # 방법 2: 텍스트 내용 기반 감지
            # Excel 형식 특징
            if "플러스엑스 정산" in text and "유니온 정산" in text:
                return "excel_format"

            if "R/S" in text and "정산 내역" in text:
                return "excel_format"

            # HTML 형식 특징 (새 양식)
            if "프로모션 매출액" in text or (
                "계약\n조건" in text and "정산금액" in text
            ):
                return "html_format"

            # 방법 3: 페이지 수 기반 (휴리스틱)
            # 새 양식은 월별이므로 다중 페이지 (보통 6페이지)
            if len(pdf.pages) > 1:
                # 추가 검증
                if "프로모션" in text or "마케팅비" in text:
                    return "html_format"

            return "unknown"

    except Exception as e:
        print(f"양식 감지 실패: {e}")
        return "unknown"


def parse_html_format_pdf(
    pdf_path: str,
    period: str,
    base_path: str
) -> ParsedSettlementData:
    """
    새 HTML 인쇄 양식 파서 (2025년 4분기 이후)

    구조:
    - 다중 페이지 (월별 또는 기업별)
    - 각 페이지: 헤더 + 정산 테이블
    - 컬럼: 항목|매출액|프로모션매출액|제작비|마케팅비|계약조건(%)|정산금액

    Returns:
        ParsedSettlementData (settlement_rows 포함)
    """
    mapping = load_course_mapping(base_path)
    result = ParsedSettlementData(
        metadata={
            "source": pdf_path,
            "period": period,
            "type": "quarterly",
            "format": "html",
        }
    )

    with pdfplumber.open(pdf_path) as pdf:
        # 모든 페이지에서 데이터 추출
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            rows = _parse_html_page_text(text, period, mapping, page_idx)
            result.settlement_rows.extend(rows)

    return result


def _parse_html_page_text(
    text: str,
    period: str,
    mapping: dict,
    page_idx: int = 0
) -> List[CourseSettlementRow]:
    """
    HTML 양식 페이지에서 정산 데이터 추출 (텍스트 기반)

    포맷 예시:
    2510_[쉐어엑스]플러스엑스 생성 AI를 활용한 커 1,384,000 692,000 0 133,864 65% 1,262,389
    머셜 아트웍 제작

    또는 (강의명이 짧은 경우):
    2510_[쉐어엑스] BKID 강의명 1,071,000 985,500 0 133,864 75% 1,441,977

    핵심: 코스ID 패턴(YYYYM_)을 먼저 찾고, 섹션은 나중에 감지
    """
    rows = []
    lines = text.split("\n")
    current_section = "unknown"
    current_ratio = 0.0

    for line_idx, line in enumerate(lines):
        line = line.strip()

        # 먼저 코스ID 패턴 찾기 (YYYYM_ 형식, 예: 2510_)
        # 새 양식: "2510_[쉐어엑스]강의명 숫자들..."
        course_match = re.search(r'\b(\d{4}[A-Z]?)_', line)

        # 코스ID가 없으면 섹션 감지 시도
        if not course_match:
            # 섹션 감지: 헤더 라인만 (강의 라인은 아님)
            # "강사명 플러스엑스" 또는 "정산 섹션" 같은 명확한 헤더만
            if not any(digit in line for digit in "0123456789"):  # 숫자 없는 라인만
                if "플러스엑스" in line and "유니온" not in line:
                    current_section = "plusx"
                    current_ratio = 0.70
                elif "유니온" in line or "BKID" in line:
                    current_section = "union"
                    current_ratio = 0.75
            continue

        # 헤더 행, 합계 행 스킵 (코스ID 있어도)
        if any(
            kw in line
            for kw in [
                "항목",
                "매출액",
                "프로모션",
                "제작비",
                "마케팅비",
                "계약",
                "합계",
                "정산금액",
                "코스아이디",
            ]
        ):
            continue

        # 섹션이 "unknown"이면 강의명 기반으로 섹션 결정
        section_for_row = current_section
        ratio_for_row = current_ratio

        if current_section == "unknown":
            # 강의명에서 섹션 추측
            if "플러스엑스" in line or "Plus X" in line:
                section_for_row = "plusx"
                ratio_for_row = 0.70
            elif "BKID" in line or "허스키" in line or "블센" in line:
                section_for_row = "union"
                ratio_for_row = 0.75
            else:
                # 기본값: union (대부분이 union)
                section_for_row = "union"
                ratio_for_row = 0.75

        # 데이터 행 파싱 (코스ID 있음)
        settlement_row = _parse_html_data_line(
            line, period, section_for_row, ratio_for_row, mapping
        )

        if settlement_row:
            rows.append(settlement_row)

    return rows


def find_best_course_match(
    course_name_pdf: str,
    mapping: dict,
    threshold: float = 0.85
) -> Optional[str]:
    """
    3단계 매칭 알고리즘으로 최적의 course_id 찾기

    Stage 1: 정확 일치 (정규화 후)
    Stage 2: 접두사 일치 (PDF 강의명이 잘린 경우 처리)
    Stage 3: 유사도 일치 (fuzzy match, threshold >= 0.85)

    Args:
        course_name_pdf: PDF에서 추출한 강의명
        mapping: course_mapping dict
        threshold: 최소 유사도 (0.0~1.0)

    Returns:
        course_id 또는 None (매칭 실패 시)

    Examples:
        >>> mapping = {"213930": {"course_name": "[쉐어엑스]플러스엑스 UI 실무 마스터 패키지"}}
        >>> find_best_course_match("[쉐어엑스]플러스엑스 UI 실무 마스터 패키", mapping)
        '213930'
    """
    normalized_pdf = normalize_course_name(course_name_pdf)

    # Stage 1: 정확 일치 (정규화 후)
    for course_id, course_info in mapping.items():
        normalized_map = normalize_course_name(course_info.get("course_name", ""))
        if normalized_pdf == normalized_map:
            return course_id

    # Stage 2: 접두사 일치 (PDF 강의명이 잘렸을 경우)
    for course_id, course_info in mapping.items():
        normalized_map = normalize_course_name(course_info.get("course_name", ""))

        # PDF가 mapping의 앞부분 (잘린 버전)
        if normalized_map.startswith(normalized_pdf):
            return course_id

        # mapping이 PDF의 앞부분 (드문 경우)
        if normalized_pdf.startswith(normalized_map):
            return course_id

    # Stage 3: 유사도 기반 매칭 (fuzzy match)
    best_score = 0.0
    best_match = None

    for course_id, course_info in mapping.items():
        normalized_map = normalize_course_name(course_info.get("course_name", ""))

        # 유사도 계산 (0.0~1.0)
        similarity = SequenceMatcher(None, normalized_pdf, normalized_map).ratio()

        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = course_id

    return best_match


def _parse_html_data_line(
    line: str,
    period: str,
    section: str,
    ratio: float,
    mapping: dict
) -> Optional[CourseSettlementRow]:
    """
    HTML 양식의 단일 데이터 라인 파싱

    포맷:
    2510_[쉐어엑스]강의명 매출액 프로모션 제작비 마케팅비 계약조건 정산금액

    핵심:
    - 라인 끝에서부터 뒤로 숫자 추출 (기존 파서와 동일)
    - 마지막 6개 숫자: 프로모션매출액, 제작비, 마케팅비, 계약조건(%), 정산금액
    - 그 앞: 매출액
    """
    try:
        # 코스ID와 강의명 추출
        course_id_match = re.search(r'(\d{4}[A-Z]?)_(.+?)(\d{1,3}%|\d{1,3}?,?\d{1,})', line)
        if not course_id_match:
            return None

        course_code = course_id_match.group(1)  # 예: "2510"
        course_name_part = course_id_match.group(2).strip()  # 예: "[쉐어엑스]강의명"

        # 라인 끝에서부터 숫자 추출 (최대 7개: 매출액, 프로모션, 제작비, 마케팅, 계약%, 정산금액)
        nums = _extract_numbers_from_right_html(line)

        if len(nums) < 6:
            # 필요한 최소 숫자 부족
            return None

        # 숫자 할당 (뒤에서부터)
        settlement_amount = nums[-1]  # 정산금액
        contract_ratio = nums[-2]     # 계약조건 (%)
        marketing_cost = nums[-3]     # 마케팅비
        production_cost = nums[-4]    # 제작비
        promo_revenue = nums[-5]      # 프로모션 매출액
        revenue = nums[-6]            # 매출액

        # 추가 숫자가 있으면 그것도 매출액으로 간주
        if len(nums) > 6:
            # 불명확한 경우, 맨 첫 숫자는 무시
            pass

        # 3단계 매칭 알고리즘으로 course_id 찾기
        course_id = find_best_course_match(course_name_part, mapping, threshold=0.85)

        if not course_id:
            # 매핑 실패 - 임시 ID 생성 (경고 로그)
            course_id = course_code + "0"
            print(f"⚠️  매칭 실패: {course_name_part[:50]}... → 임시ID {course_id}")

        # 광고비 역산 (매출액 - 공헌이익)
        # 공헌이익 = 매출액 - 광고비 (제작비 + 마케팅비 포함)
        ad_cost = production_cost + marketing_cost

        # 공헌이익 계산
        # 정산금액 = 공헌이익 * 계약조건 비율
        # 역산: 공헌이익 = 정산금액 / 계약조건 비율
        if contract_ratio > 0:
            contribution = settlement_amount / contract_ratio
        else:
            contribution = revenue - ad_cost

        return CourseSettlementRow(
            period=period,
            course_id=course_id,
            course_name=course_name_part,
            revenue=revenue,
            ad_cost=ad_cost,
            contribution_margin=contribution,
            revenue_share_fee=settlement_amount,
            section=section,
            rs_ratio=ratio,
        )

    except (IndexError, ValueError, TypeError, ZeroDivisionError) as e:
        # 파싱 실패는 조용히 무시
        return None


def _extract_numbers_from_right_html(line: str) -> List[float]:
    """
    HTML 양식에서 라인 끝부터 뒤로 숫자 추출

    새 양식의 숫자 형식: "1,384,000" 또는 "65%" 등
    """
    tokens = line.split()
    nums = []

    # 뒤에서부터 숫자 토큰 추출
    for token in reversed(tokens):
        # 백분율 처리 (예: "65%" → 0.65)
        if token.endswith("%"):
            try:
                ratio = float(token.rstrip("%")) / 100
                nums.insert(0, ratio)
            except ValueError:
                break
        # 쉼표가 포함된 숫자 (예: "1,384,000")
        elif re.match(r'^[\d,]+$', token):
            val = clean_numeric(token)
            if val is not None:
                nums.insert(0, val)
        # 숫자만 (예: "0")
        elif re.match(r'^\d+$', token):
            nums.insert(0, float(token))
        else:
            # 숫자가 아닌 토큰 만남 → 중단
            # 단, 텍스트 끝에 붙은 숫자가 있으면 추출
            tail_match = re.search(r'([\d,]+)$', token)
            if tail_match:
                val = clean_numeric(tail_match.group(1))
                if val is not None:
                    nums.insert(0, val)
            break

    return nums
