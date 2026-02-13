"""
Company 데이터 모델
==================
기업 정보 및 정산 결과 데이터 클래스
"""

from dataclasses import dataclass, field


@dataclass
class Company:
    """기업 정보"""
    company_id: str
    name: str
    type: str  # "운영사", "유니온", "유니온(신규)"
    biz_number: str = ""
    bank: str = ""
    account: str = ""
    contact_name: str = ""
    contact_email: str = ""
    tax_email: str = ""
    phone: str = ""
    contract_start: str = ""
    contract_end: str = ""
    address: str = ""
    representative: str = ""
    account_holder: str = ""
    
    # 수익쉐어 비율 (Phase 1 추가)
    revenue_share_ratio: float = 0.75  # 공헌이익 대비 수익쉐어 비율
    union_payout_ratio: float = 0.50   # 유니온 실지급 비율
    payout_calculation: str = "standard"  # "full", "shared_20_40", "shared_50_25", "standard"


@dataclass
class CompanySettlement:
    """기업별 정산 결과"""
    company_id: str
    company_name: str
    period: str  # "YYYY-QN" (e.g., "2024-Q4")

    # 매출
    total_revenue: float = 0.0
    course_revenues: dict = field(default_factory=dict)  # {course_id: revenue}

    # 광고비
    direct_ad_cost: float = 0.0
    indirect_ad_cost: float = 0.0
    total_ad_cost: float = 0.0

    # 정산 금액
    contribution_margin: float = 0.0  # 공헌이익 = 매출 - 광고비
    revenue_share_fee: float = 0.0  # 수익쉐어 강사료
    union_payout: float = 0.0  # 유니온 실지급 강사료
    plusx_share: float = 0.0  # 플러스엑스 몫 (제3자 계약)

    # 안분 상세
    course_count: int = 0
    indirect_ad_per_course: float = 0.0

    # 메타데이터
    revenue_share_ratio: float = 0.75  # 기본값 75%
    union_payout_ratio: float = 0.50  # 유니온 비율
    
    # 정산 상태 (Phase 1 추가)
    status: str = "normal"  # "normal", "deferred", "excluded"
    deferred_to_next_quarter: bool = False
    deferred_amount: float = 0.0
