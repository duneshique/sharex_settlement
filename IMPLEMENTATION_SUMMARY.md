# ShareX Settlement Processing - Implementation Summary

**Date:** February 11, 2026
**Status:** ✓ Core Pipeline Completed

## 완료된 기능

### 1. Monthly PDF Processing ✓
- **위치:** `src/core/monthly_processor.py`
- **기능:**
  - FastCampus 월별 정산 PDF 파싱
  - 강의별 매출 데이터 추출
  - 강의 → 회사 매핑 (course_mapping.json 기반)
  - **광고비 분류 및 할당:**
    - 직접광고비: 특정 회사에 직접 할당
    - 간접광고비: 전체 활성 강의 수로 균등 배분
  - 회사별 정산 금액 계산 (revenue_share_ratio, union_payout_ratio 적용)
  - Monthly settlement JSON 생성

### 2. Quarterly Consolidation ✓
- **위치:** `src/core/quarterly_consolidator.py`
- **기능:**
  - 3개 월별 settlement JSON 파일 자동 검색
  - 회사별 분기 데이터 집계
  - 월별 breakdown 포함 분기 consolidated JSON 생성
  - PDF 검증 프레임워크 (구현 완료, PDF 파서 개선 필요)

### 3. Cost Calculation Logic ✓
- **Campaign 분류 시스템:**
  - `config/campaign_rules.json` 기반 자동 분류
  - Target 필드 우선 사용 (SHARE X, PLUS X, BKID, etc.)
  - Campaign 이름 패턴 매칭 fallback
- **Cost 할당 공식:**
  ```
  직접광고비: 100% → 해당 회사
  간접광고비: 총 간접광고비 ÷ 전체 강의 수 × 회사 강의 수
  ```
- **정산 계산:**
  ```
  공헌이익 = 매출 - 광고비
  정산액 = 공헌이익 × revenue_share_ratio × union_payout_ratio
  ```

### 4. Test Pipeline ✓
- **위치:** `test_pipeline.py`
- **기능:**
  - End-to-end 파이프라인 테스트
  - 2025 Q4 (Oct, Nov, Dec) 완전 처리 검증
  - 정산 금액 summary 출력

## 테스트 결과 (2025 Q4)

| Company | Q4 Settlement (KRW) |
|---------|---------------------|
| BKID | 8,904,916 |
| 허스키폭스 | 3,437,086 |
| HEAZ | 2,985,740 |
| 코스믹레이 | 2,571,190 |
| 아뜰리에동가 | 1,211,963 |
| 디파이 | 865,040 |
| 시싸이드시티 | 696,940 |
| 폰트릭스 | 657,540 |
| 주식회사 산돌 | 624,240 |
| 김형준 | 304,865 |
| Compound-C | -125,010 |
| 플러스엑스 | 0 |
| 디자인하우스 | 0 |
| **TOTAL** | **22,134,512** |

## 출력 파일 구조

```
output/
└── 2025-Q4/
    ├── 2025-10_settlement.json    # 10월 정산
    ├── 2025-11_settlement.json    # 11월 정산
    ├── 2025-12_settlement.json    # 12월 정산
    └── 2025-Q4_consolidated.json  # 분기 통합 정산
```

### Monthly Settlement JSON Structure
```json
{
  "period": "2025-10",
  "extraction_date": "2026-02-11T16:21:11",
  "source_file": "[패스트캠퍼스] Share X 정산서 - 2025년 10월.pdf",
  "companies": {
    "huskyfox": {
      "company_name": "허스키폭스",
      "total_revenue": 1696000.0,
      "total_cost": 313893.22,
      "contribution_margin": 1382106.78,
      "revenue_share_ratio": 0.75,
      "union_payout_ratio": 0.5,
      "settlement_amount": 691053.39,
      "course_count": 4
    }
  }
}
```

### Quarterly Consolidated JSON Structure
```json
{
  "period": "2025-Q4",
  "consolidation_date": "2026-02-11T16:21:52",
  "monthly_files": ["2025-10", "2025-11", "2025-12"],
  "companies": {
    "huskyfox": {
      "company_name": "허스키폭스",
      "monthly": [
        {
          "month": "2025-10",
          "revenue": 1696000.0,
          "cost": 313893.22,
          "contribution": 1382106.78,
          "settlement": 691053.39
        },
        // ... Nov, Dec
      ],
      "q4_totals": {
        "total_revenue": 6886250.0,
        "total_cost": 1811692.22,
        "total_contribution": 5074557.78,
        "q4_settlement": 3437086.0
      }
    }
  },
  "validation": {
    "status": "pending",
    "note": "PDF validation framework ready, parser needs enhancement"
  }
}
```

## 향후 개선 사항

### 1. PDF Validation Enhancement (Priority: HIGH)
- **현재 상태:** 검증 프레임워크 완료, PDF 파서 개선 필요
- **문제:** 2025 Q4 quarterly PDF에서 데이터 파싱 실패 (0 rows)
- **조치 필요:**
  - `parse_quarterly_pdf()` 함수 디버깅
  - 2025 PDF 포맷 변경사항 분석
  - Pattern matching 로직 개선

### 2. Command-Line Interface (Priority: MEDIUM)
```bash
# 월별 처리
python -m sharex.cli process-monthly \
  --pdf path/to/pdf \
  --month 2025-10

# 분기 통합
python -m sharex.cli consolidate-quarterly \
  --period 2025-Q4 \
  --validate-pdf path/to/quarterly.pdf
```

### 3. Automation Triggers (Priority: MEDIUM)
- 3개 월별 파일 생성 시 자동 quarterly consolidation
- Email notification on completion
- Error logging and alerting

### 4. Web Service Wrapper (Priority: LOW)
- FastAPI 기반 REST API
- PDF 업로드 endpoint
- 정산 데이터 조회 API
- 검증 결과 dashboard

### 5. Historical Data Processing (Priority: LOW)
- 2024 Q1-Q4 과거 데이터 처리
- 2025 Q1-Q3 데이터 처리
- Historical trend analysis

## 실행 방법

### 테스트 실행
```bash
# Full pipeline test
PYTHONPATH=".:./src" python test_pipeline.py

# 특정 월 처리
python -c "
import sys
sys.path.insert(0, 'src')
from core.monthly_processor import MonthlyProcessor

processor = MonthlyProcessor('.')
result = processor.process_monthly_pdf(
    'archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - 2025년 10월.pdf',
    '2025-10'
)
processor.save_monthly_settlement(result)
"
```

### 분기 통합
```bash
python -c "
import sys
sys.path.insert(0, 'src')
from core.quarterly_consolidator import QuarterlyConsolidator

consolidator = QuarterlyConsolidator('.')
result = consolidator.consolidate_quarter('2025-Q4')
consolidator.save_consolidated_quarterly(result)
"
```

## 기술 스택

- **Language:** Python 3.9+
- **PDF Parsing:** pdfplumber
- **Data Models:** dataclasses
- **Configuration:** JSON files (companies.json, course_mapping.json, campaign_rules.json)
- **Testing:** Custom test pipeline

## 파일 맵

| File | Purpose |
|------|---------|
| `src/core/monthly_processor.py` | 월별 PDF 처리 |
| `src/core/quarterly_consolidator.py` | 분기 통합 |
| `src/parsers/fastcampus_pdf.py` | PDF 파서 |
| `src/models/company.py` | Company 데이터 모델 |
| `data/companies.json` | 회사 설정 (13개 회사) |
| `data/course_mapping.json` | 강의 매핑 (42개 강의) |
| `config/campaign_rules.json` | 광고 분류 규칙 |
| `test_pipeline.py` | End-to-end 테스트 |

## 주요 개선사항 이력

1. **Cost Calculation Fix (2026-02-11)**
   - Before: 단순 매출 비례 배분
   - After: 직접/간접 광고비 분류 후 강의당 균등 배분
   - Impact: 정산액 약 175K KRW 차이 (더 정확해짐)

2. **PDF Validation Framework (2026-02-11)**
   - Quarterly PDF 파싱 → 회사별 집계 → 계산값 비교
   - 100 KRW 오차 허용 (rounding)
   - 검증 결과 JSON에 저장

3. **Import Path Fixes (2026-02-11)**
   - Lazy import in `src/core/__init__.py`
   - Absolute imports in monthly_processor
   - Module import 순환 참조 해결

## 성능

- **월별 처리 시간:** ~5초/PDF
- **분기 통합 시간:** <1초
- **총 파이프라인 시간 (3 months):** ~15-20초

## 결론

ShareX Settlement Processing 파이프라인의 **핵심 기능이 완성**되었습니다:
✓ 월별 PDF 처리
✓ 올바른 광고비 분류 및 할당
✓ 회사별 정산 계산
✓ 분기 통합

**남은 작업:**
- PDF 검증 파서 개선 (2025 포맷 대응)
- CLI 및 자동화 wrapper
- Historical data processing
