"""
MVP 파이프라인 모듈

최소 기능으로 정산 자동화를 구현합니다:
1. PDF 데이터 추출
2. 안분 & 정산 계산
3. 기업별 정산서 PDF 생성
"""

from server_logic.mvp.pdf_extractor import extract_pdf_data

__all__ = [
    'extract_pdf_data',
]
