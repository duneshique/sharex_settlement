# 미사용 코드 (Deprecated Code)

이 디렉토리는 **MVP 파이프라인에서 사용하지 않는 구형 코드**를 정리한 폴더입니다.

## 📌 현재 MVP 워크플로우 (활성 사용)

```
run_mvp.py
├── src/mvp/pdf_extractor.py      ✓ Step 1: PDF 추출
├── src/mvp/settlement_calculator.py ✓ Step 2: 정산 계산
└── src/mvp/pdf_generator.py      ✓ Step 3: PDF 생성
```

**사용 중인 파서들** (src/parsers/):
- `base.py` - 기본 데이터 모델 및 유틸리티
- `fastcampus_pdf.py` - 패스트캠퍼스 PDF 파싱
- `unified_pdf_parser.py` - 통합 PDF 파서 (양식 자동 감지)

---

## 📁 미사용 코드 목록

### 1️⃣ **Phase 0 (구형 파이프라인)**
- `src/unused/pipeline.py` - 구형 main pipeline (Phase 0 검증용)
- `src/unused/apportionment.py` - 위치 이동됨 (src/core/apportionment.py로 통합)

### 2️⃣ **Core 모듈** (검증 스크립트 전용)
```
src/unused/core/
├── pipeline.py             - 구형 분기별 처리 파이프라인
├── quarterly_consolidator.py - 분기 데이터 통합 (미사용)
├── monthly_processor.py    - 월별 처리 로직 (미사용)
└── apportionment.py        - Phase 0 검증용 배분 엔진
```

사용처: `scripts/validation_phase0.py`, `scripts/validate_imports.py`

### 3️⃣ **Parsers** (테스트 전용)
```
src/unused/parsers/
├── union_pdf.py          - 유니온별 PDF 파서 (test_union_parser.py에서만 사용)
└── excel_settlement.py   - Excel 정산서 파서 (미사용)
```

### 4️⃣ **Reports** (구형 리포팅)
```
src/unused/reports/
└── excel_report.py       - Excel 리포트 생성 (run_settlement.py에서만 사용)
```

### 5️⃣ **~~API~~ (활성 복원됨)**
**⚠️ API는 웹 대시보드 사용 시 필요하므로 `src/api/`로 복원되었습니다.**

### 6️⃣ **Models** (구형 모델)
```
src/unused/models/
├── campaign.py
├── company.py
├── course.py
└── validation.py
```

사용처: Phase 0 검증 스크립트에서만 사용 (MVP는 dict 기반)

---

## ⚠️ 정리 대상 스크립트

이 미사용 코드를 사용하는 스크립트들도 검토 필요:
- `scripts/run_settlement.py` - 구형 파이프라인 (MVP로 대체)
- `scripts/validation_phase0.py` - Phase 0 검증용 (보관 가능)
- `scripts/validate_imports.py` - 모듈 임포트 검증용 (필요 시 실행)
- `scripts/test_union_parser.py` - 유니온 파서 테스트 (미사용)
- `scripts/diagnose_parser.py` - 파서 진단 도구 (선택)

---

## 🔄 복원 방법

미사용 코드가 다시 필요하면:

```bash
# 예: apportionment 모듈 복원
mv src/unused/core/apportionment.py src/core/

# 예: Models 모듈 복원
mv src/unused/models src/
```

---

## 📝 정책

- MVP 파이프라인(`run_mvp.py`)에 불필요한 코드는 이곳으로 이동
- 정리된 코드는 **git에서 추적 중단**하여 코드베이스 복잡도 감소
- Phase 0 검증 스크립트는 필요시 참고할 수 있도록 보관

최종 업데이트: 2026-02-13
