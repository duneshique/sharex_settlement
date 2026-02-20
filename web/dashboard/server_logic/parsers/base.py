"""
공통 데이터 클래스 및 유틸리티
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CourseSales:
    """강의별 매출 데이터"""
    month: str          # "YYYY-MM"
    course_id: str
    course_name: str
    company_id: str
    revenue: float


@dataclass
class CampaignCost:
    """캠페인별 광고비"""
    month: str          # "YYYY-MM"
    channel: str        # "Google", "Meta", "Naver"
    target: str         # "SHARE X", "PLUS X", "BKID", etc.
    campaign_name: str
    cost_krw: float
    cost_usd: float = 0.0
    exchange_rate: float = 0.0


@dataclass
class CourseSettlementRow:
    """FastCampus 분기 정산서에서 추출한 강의별 정산 행 (확정 데이터)"""
    period: str         # "2024-Q4"
    course_id: str
    course_name: str
    revenue: float
    ad_cost: float
    contribution_margin: float
    revenue_share_fee: float
    section: str        # "plusx" or "union"
    rs_ratio: float     # 0.70 or 0.75


@dataclass
class ParsedSettlementData:
    """파싱된 정산 데이터 통합 구조"""
    course_sales: List[CourseSales] = field(default_factory=list)
    campaign_costs: List[CampaignCost] = field(default_factory=list)
    settlement_rows: List[CourseSettlementRow] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ──────────────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────────────

def clean_numeric(value) -> Optional[float]:
    """
    숫자 정제: 콤마, ₩, -, 공백, 특수문자 처리

    Args:
        value: 정제할 값 (str, int, float, None)

    Returns:
        float 또는 None (파싱 불가 시)
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()

    # "-" 만 있으면 0 또는 None
    if s in ("-", "—", "–", ""):
        return None

    # 특수문자 제거: ₩, \, 콤마, 공백, non-breaking space
    s = re.sub(r'[₩\\,\s\u00a0\u202d\u202c]', '', s)

    # 퍼센트 제거
    s = s.replace('%', '')

    try:
        return float(s)
    except ValueError:
        return None


def normalize_course_name(name: str) -> str:
    """
    강의명 정규화 (매칭 개선용)

    처리 순서:
    1. Unicode NFC 정규화 (macOS 호환)
    2. 좌우 공백 제거
    3. 연속 공백 → 단일 공백
    4. 괄호 뒤 공백 제거: "] " → "]"
    5. 특수 공백 문자 제거

    Args:
        name: 원본 강의명

    Returns:
        정규화된 강의명

    Examples:
        >>> normalize_course_name("[쉐어엑스] Plus X")
        '[쉐어엑스]Plus X'
        >>> normalize_course_name("  강의명  테스트  ")
        '강의명 테스트'
    """
    import unicodedata

    # Unicode NFC 정규화
    name = unicodedata.normalize("NFC", name)

    # 특수 공백 문자 제거 (정규 표현식 전에 수행)
    name = name.replace('\u00a0', '').replace('\u202d', '').replace('\u202c', '')

    # 좌우 공백 제거
    name = name.strip()

    # 연속 공백 → 단일 공백
    name = re.sub(r'\s+', ' ', name)

    # 괄호 앞뒤 공백 제거
    name = name.replace('] ', ']').replace(' ]', ']')
    name = name.replace('[ ', '[').replace(' [', '[')

    return name


def parse_quarter_months(period: str) -> List[str]:
    """
    분기 문자열에서 월 리스트 추출
    예: "2024-Q4" → ["2024-10", "2024-11", "2024-12"]
    """
    year, q = period.split("-Q")
    q = int(q)
    start_month = (q - 1) * 3 + 1
    return [f"{year}-{start_month + i:02d}" for i in range(3)]


def parse_month_from_text(text: str) -> Optional[str]:
    """
    텍스트에서 월 정보 추출
    예: "2024년 10월" → "2024-10"
        "2024. 4Q" → None (분기)
        "24.10" → "2024-10"
    """
    # "2024년 10월" 패턴
    m = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월', text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    # "24.10" 패턴
    m = re.search(r'(\d{2})\.(\d{2})', text)
    if m:
        year = 2000 + int(m.group(1))
        month = int(m.group(2))
        if 1 <= month <= 12:
            return f"{year}-{month:02d}"

    return None


def load_course_mapping(base_path: str) -> Dict[str, dict]:
    """
    course_mapping.json 로드

    Returns:
        {course_id: {"company_id": str, "course_name": str, ...}}
    """
    path = Path(base_path) / "data" / "course_mapping.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    for course in data["courses"]:
        mapping[course["course_id"]] = course

    return mapping


def get_course_company_id(course_id: str, mapping: Dict[str, dict]) -> Optional[str]:
    """course_id로 company_id 조회"""
    course = mapping.get(course_id)
    if course:
        return course["company_id"]
    return None
