# ShareX MVP 개발 상태 리포트

**기준일**: 2025년 2월 13일
**상태**: ✅ **MVP 파이프라인 완성 및 검증 통과**

---

## 📊 개발 현황

### 완료된 기능 (4/4)

| 단계 | 항목 | 상태 | 파일 | 핵심 구현 |
|------|------|------|------|---------|
| **Step 1** | PDF 데이터 추출 | ✅ | `src/mvp/pdf_extractor.py` | 통합 파서 (기존/새 양식 자동 감지) |
| **Step 2** | 정산 계산 | ✅ | `src/mvp/settlement_calculator.py` | 기업별 동적 payout_ratio 적용 |
| **Step 3** | 월별 PDF 추출 | ✅ | `src/mvp/pdf_extractor.py:139-183` | `extract_quarterly_with_monthly()` |
| **Step 4** | 정산서 PDF 생성 | ✅ | `src/mvp/pdf_generator.py` | HTML→PDF 변환 (weasyprint) |

### 2024-Q4 검증 결과

```
📥 입력
  - 분기 PDF: [패스트캠퍼스] Share X 정산서 - 2024년 4Q.pdf (1페이지)
  - 추출 강의: 37개
  - 총 매출: 270,157,820원

🔄 처리
  - 기업별 그룹화: 13개 기업
  - 동적 payout_ratio 적용: 각 기업별 설정값 사용
  - 총 정산액: 159,250,722원

✅ 출력
  - 정산 결과 JSON: 13개 기업 정산 데이터
  - 정산서 PDF: 12개 생성 완료
  - 검증: 11개 기업 32,708,346.5원 ✅ (±1원 이내)
```

### CLI 사용법

```bash
# 기본 실행 (분기 전용)
python3 scripts/run_mvp.py --period 2024-Q4

# 월별 breakdown 포함
python3 scripts/run_mvp.py --period 2024-Q4 --monthly

# 특정 단계만 실행
python3 scripts/run_mvp.py --period 2024-Q4 --step extract
python3 scripts/run_mvp.py --period 2024-Q4 --step calculate
python3 scripts/run_mvp.py --period 2024-Q4 --step generate

# 검증 포함
python3 scripts/run_mvp.py --period 2024-Q4 --validate
```

---

## 🔧 기술 스택

| 계층 | 기술 | 파일 |
|------|------|------|
| **PDF 파싱** | pdfplumber 0.11.9 | `src/parsers/fastcampus_pdf.py` |
| **PDF 생성** | weasyprint 68.1 | `src/mvp/pdf_generator.py` |
| **데이터 처리** | pandas 3.0.0 | `src/mvp/settlement_calculator.py` |
| **설정 관리** | JSON | `data/companies.json`, `data/course_mapping.json` |
| **CLI** | argparse | `scripts/run_mvp.py` |

---

## 📁 출력 파일 구조

```
output/2024-Q4/
├── intermediate_data.json          # Step 1 출력 (37개 강의 데이터)
├── settlement_result.json          # Step 2 출력 (13개 기업 정산액)
└── 쉐어엑스_*.pdf (12개)           # Step 3 출력
    ├── 쉐어엑스_ BKID 24년 4Q 정산서.pdf
    ├── 쉐어엑스_ HEAZ 24년 4Q 정산서.pdf
    ├── ... (총 12개)
```

---

## ⚠️ 현황 및 개선사항

### 현재 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| 2024 Q4 파이프라인 | ✅ | 37개 강의 추출, 검증 통과 |
| 2025 Q4 (새 양식) | 🔄 진행중 | HTML 인쇄 PDF 파서 개발 중 |
| 웹 대시보드 | 🟡 미완성 | Next.js 프론트엔드 API 미연동 |
| 월별 breakdown | ✅ | 기능 구현 완료, 월별 PDF 필요 |

### PDF 파서 현황

**기존 형식** (Excel→PDF, 2024-Q4):
- ✅ 1페이지, 텍스트 기반
- ✅ 코스ID (5자리: 21xxxx~24xxxx) 기반 파싱
- ✅ 37개 강의 추출 성공

**새 형식** (HTML 인쇄, 2025-Q4):
- ✅ 다중 페이지 (월별 또는 기업별 6페이)
- ✅ 코스ID (4자리 월코드: 2510_, 2511_, 2512_) 패턴
- 🔄 강의명 기반 매칭 (현재 76/128 강의 추출 중)
- ⚠️ 52개 강의 누락 → 추가 작업 필요

### 주요 이슈

1. **새 양식 파서 완성도**
   - 현재: 76개 강의 추출 (59% success rate)
   - 문제: 강의명 부분 일치 매칭 미흡
   - 해결책: course_mapping.json과 강의명 정규화 필요

2. **PDF 템플릿 시각화**
   - 기존 파일: `archive/Union_Profit Share_Settlement/` (350KB)
   - 신규 파일: `output/2024-Q4/` (41-62KB)
   - 확인 필요: 레퍼런스와의 시각적 일치 여부

3. **월별 breakdown**
   - 기능: ✅ 구현 완료
   - 요구: 월별 PDF 3개 (YYYY년 MM월.pdf)
   - 현황: 월별 PDF 자동 탐색 미완성

---

## 🚀 다음 단계

### Phase 2: 프로덕션 준비

1. **PDF 템플릿 개선** (Step 3 고도화)
   - 레퍼런스 스크린샷과 비교 검증
   - 레이아웃/스타일 최적화
   - 월별 breakdown 테이블 구현

2. **새 양식 파서 완성** (통합 파서 고도화)
   - 강의명 정규화/매칭 알고리즘
   - 52개 누락 강의 추출
   - HTML 페이지별 데이터 완전 추출

3. **웹 대시보드 연동**
   - Next.js 프론트엔드 API 클라이언트
   - FastAPI 백엔드 구현
   - 파일 업로드 → 자동 정산 → PDF 다운로드 워크플로우

### Phase 3: 운영 자동화

1. 월별 정산 자동화
2. 이메일 발송 자동화
3. 모니터링 및 에러 핸들링

---

## 📋 검증 기준

**2024 Q4 기준값**: 32,708,346.5원 (11개 기업)

| 기업 | 예상 정산액 | 자동 계산 | 차이 | 상태 |
|------|---------|----------|------|------|
| huskyfox | 6,432,849.5 | 6,432,849.5 | 0 | ✅ |
| cosmicray | 4,083,126.5 | 4,083,126.5 | 0 | ✅ |
| bkid | 4,509,514.5 | 4,509,514.5 | 0 | ✅ |
| heaz | 3,659,120.0 | 3,659,120.0 | 0 | ✅ |
| atelier_dongga | 2,392,750.5 | 2,392,750.5 | 0 | ✅ |
| fontrix | 949,759.0 | 949,759.0 | 0 | ✅ |
| dfy | 2,994,788.5 | 2,994,788.5 | 0 | ✅ |
| compound_c | 2,255,400.0 | 2,255,400.0 | 0 | ✅ |
| csidecity | 1,930,270.5 | 1,930,270.5 | 0 | ✅ |
| blsn | 1,031,299.0 | 1,031,299.0 | 0 | ✅ |
| sandoll | 2,469,468.5 | 2,469,468.5 | 0 | ✅ |
| **합계** | **32,708,346.5** | **32,708,346.5** | **0** | **✅** |

---

## 📝 참고

- **프로젝트 루트**: `/Users/plusx-junsikhwang/Documents/GitHub/ShareX_Settlement`
- **의존성**: `requirements.txt` (46개 패키지)
- **배포 가이드**: `DEPLOYMENT.md`
- **설계 문서**: `docs/PDF_PARSER_DESIGN.md`
