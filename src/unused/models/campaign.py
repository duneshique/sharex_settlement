"""
Campaign 데이터 모델
====================
광고 캠페인 비용 데이터 클래스
"""

from dataclasses import dataclass


@dataclass
class CampaignCost:
    """캠페인별 광고비"""
    month: str  # "YYYY-MM"
    channel: str  # "Google", "Meta", "Naver", "Pinterest"
    target: str  # "SHARE X", "PLUS X", "BKID", etc.
    campaign_name: str
    cost_krw: float  # KRW 금액 (VAT 포함)
    cost_usd: float = 0.0  # USD 원본 (Meta의 경우)
    exchange_rate: float = 0.0  # 적용 환율
    clicks: int = 0
    impressions: int = 0
