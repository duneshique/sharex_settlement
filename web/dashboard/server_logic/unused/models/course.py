"""
Course 데이터 모델
==================
강의 정보 및 매출 데이터 클래스
"""

from dataclasses import dataclass


@dataclass
class Course:
    """강의 정보"""
    course_id: str
    course_name: str
    company_id: str
    company_name: str
    share_type: str = "single"  # "single" or "shared"
    share_ratio: float = 1.0
    is_active: bool = True
    exclude_from_settlement: bool = False


@dataclass
class CourseSales:
    """강의별 매출 데이터"""
    month: str  # "YYYY-MM"
    course_id: str
    course_name: str
    company_id: str
    revenue: float  # 매출액
