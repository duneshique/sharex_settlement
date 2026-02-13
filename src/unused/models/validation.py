"""
Validation 데이터 모델
======================
교차검증 결과 데이터 클래스
"""

from dataclasses import dataclass


@dataclass
class ValidationResult:
    """교차검증 결과"""
    check_name: str
    passed: bool
    expected: float = 0.0
    actual: float = 0.0
    difference: float = 0.0
    tolerance: float = 1.0  # 허용 오차 (원)
    message: str = ""
