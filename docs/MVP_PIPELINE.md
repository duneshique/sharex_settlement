# ShareX Settlement MVP 파이프라인 설계

> **작성일**: 2026-02-12
> **목적**: 제로 베이스에서 최소 MVP로 정산 자동화 재구축

---

## 전체 워크플로우

```
┌─────────────────────────────────────────────────────────────────┐
│                        MVP 파이프라인                              │
└─────────────────────────────────────────────────────────────────┘

[1] PDF 수신 (수동)
    ↓
    [패스트캠퍼스] Share X 정산서 - 2025년 10~12월.pdf

[2] PDF 데이터 추출 ⚙️
    ↓
    intermediate_data.json
    {
      "period": "2025-Q4",
      "courses": [
        {"course_id": "...", "revenue": 1000000, ...}
      ]
    }

[3] 안분 & 정산 계산 ⚙️
    ↓
    settlement_result.json
    {
      "heaz": {"settlement_amount": 3659120.0, ...},
      "bkid": {"settlement_amount": 4509514.5, ...}
    }

[4] 기업별 정산서 PDF 생성 ⚙️
    ↓
    output/2025-Q4/
      ├── 쉐어엑스_ HEAZ 4Q 정산서.pdf
      ├── 쉐어엑스_ BKID 4Q 정산서.pdf
      └── ...
```

---

## Step 1: PDF 데이터 추출

### 📥 입력
- **파일**: `archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - YYYY년 MM월.pdf`
- **형식**: 패스트캠퍼스가 제공하는 분기별 또는 월별 정산서 PDF

### 🎯 목표
PDF에서 다음 정보를 추출:
1. **강의별 매출액** (코스명, 금액)
2. **광고비** (캠페인명, 금액, 매체)
3. **기타 비용** (제작비 등)

### ⚙️ 처리 로직

#### Option A: 분기별 PDF (추천)
- 파일 예시: `[패스트캠퍼스] Share X 정산서 - 2024년 4Q.pdf`
- 이미 월별 합산된 데이터 제공
- **유니온 기업별 지급액이 이미 계산되어 있음** (가장 정확)

#### Option B: 월별 PDF
- 파일 예시: `[패스트캠퍼스] Share X 정산서 - 2024년 10월.pdf`
- 3개월치 PDF를 따로 추출 후 합산 필요

### 📤 출력
```json
{
  "period": "2025-Q4",
  "extraction_date": "2026-02-12T10:30:00",
  "source_file": "[패스트캠퍼스] Share X 정산서 - 2025년 10~12월.pdf",
  "method": "quarterly_pdf",

  "courses": [
    {
      "course_id": "course_001",
      "course_name": "포토샵 완전정복",
      "revenue": 15000000,
      "company_id": "plusx"
    }
  ],

  "advertising": [
    {
      "campaign_name": "[Share X] 통합 광고",
      "amount": 5000000,
      "channel": "Google",
      "type": "indirect"  // 간접광고비
    },
    {
      "campaign_name": "[BKID] 신규 오픈 광고",
      "amount": 1000000,
      "channel": "Meta",
      "type": "direct",   // 직접광고비
      "target_company": "bkid"
    }
  ],

  "total_revenue": 100000000,
  "total_advertising": 20000000
}
```

### 🛠️ 구현 파일
- `src/mvp/pdf_extractor.py`
- 기존 파서 재사용 가능: `src/parsers/fastcampus_pdf.py`

### ✅ 검증
- 총 매출액 = 원본 PDF 합계와 일치
- 모든 코스가 `course_mapping.json`에 존재
- 광고비 캠페인명 파싱 성공률 100%

---

## Step 2: 안분 & 정산 계산

### 📥 입력
1. `intermediate_data.json` (Step 1 결과)
2. `data/course_mapping.json` (강의 → 기업 매핑)
3. `data/companies.json` (기업 정보)
4. `config/campaign_rules.json` (광고 분류 규칙)

### 🎯 목표
각 유니온 기업별 정산 금액 계산:
```
정산 금액 = (매출 - 직접광고비 - 간접광고비) × 수익쉐어 비율 × 유니온 비율
```

### ⚙️ 처리 로직

#### 2.1 강의 → 기업 매핑
```python
course_mapping.json:
{
  "course_001": {
    "companies": {
      "plusx": 1.0  # 단독 제공 100%
    }
  },
  "course_002": {
    "companies": {
      "huskyfox": 0.5,  # 공동 제공 50:50
      "plusx": 0.5
    }
  }
}
```

#### 2.2 광고비 분류
- **직접광고비**: 특정 기업 대상 캠페인 → 해당 기업에만 귀속
- **간접광고비**: "Share X" 통합 광고 → 전체 강의 수로 균등 안분

```python
간접광고비 안분 = 총 간접광고비 ÷ 전체 강의 수 × 기업 강의 수
```

#### 2.3 정산 금액 계산
```python
for company in companies:
    # 1. 매출 집계
    revenue = sum(course.revenue * mapping[course][company] for course in courses)

    # 2. 직접광고비
    direct_ad = sum(ad.amount for ad in ads if ad.target == company)

    # 3. 간접광고비 안분
    indirect_ad = total_indirect_ad / total_courses * company.course_count

    # 4. 공헌이익
    contribution = revenue - direct_ad - indirect_ad

    # 5. 수익쉐어 강사료
    share_rate = 0.75  # 75% (기본값)
    revenue_share = contribution * share_rate

    # 6. 유니온 실지급액
    union_ratio = 2/3  # 플엑 몫 제외
    settlement = revenue_share * union_ratio
```

### 📤 출력
```json
{
  "period": "2025-Q4",
  "calculation_date": "2026-02-12T10:35:00",

  "companies": {
    "heaz": {
      "company_name": "HEAZ",
      "revenue": 10000000,
      "direct_advertising": 500000,
      "indirect_advertising": 300000,
      "contribution": 9200000,
      "revenue_share": 6900000,
      "union_payout": 4600000,
      "settlement_amount": 3659120.0
    },
    "bkid": {
      "company_name": "BKID",
      "settlement_amount": 4509514.5
    }
  },

  "total_settlement": 32708346.5,

  "validation": {
    "total_revenue_matched": true,
    "total_advertising_matched": true,
    "ground_truth_diff": 0.0  // ±1원 이내
  }
}
```

### 🛠️ 구현 파일
- `src/mvp/settlement_calculator.py`
- 기존 엔진 재사용: `src/apportionment.py` 또는 `src/core/apportionment.py`

### ✅ 검증
- 모든 기업 정산 금액 합계 = 확정 정산 금액 (24년 4Q: 32,708,346.5원)
- 각 기업별 금액 = `archive/Union_Profit Share_Settlement/` PDF 금액과 ±1원 이내

---

## Step 3: 기업별 정산서 PDF 생성

### 📥 입력
- `settlement_result.json` (Step 2 결과)
- PDF 템플릿 (선택사항)

### 🎯 목표
각 유니온 기업별로 정산서 PDF 생성:
```
output/2025-Q4/
  ├── 쉐어엑스_ HEAZ 4Q 정산서.pdf
  ├── 쉐어엑스_ BKID 4Q 정산서.pdf
  ├── 쉐어엑스_ 코스믹레이 4Q 정산서.pdf
  └── ...
```

### ⚙️ 처리 로직

#### 3.1 PDF 레이아웃
```
┌─────────────────────────────────────────┐
│   Share X 정산서 - 2025년 4분기           │
│                                         │
│   수신: HEAZ                             │
│   발행일: 2026-02-12                     │
│                                         │
│   1. 매출액:        10,000,000원         │
│   2. 광고비:         1,200,000원         │
│   3. 공헌이익:       8,800,000원         │
│   4. 수익쉐어:       6,600,000원         │
│   5. 정산 금액:      3,659,120원         │
│                                         │
│   계좌: [기업별 계좌번호]                 │
│   담당자: [담당자명]                     │
└─────────────────────────────────────────┘
```

#### 3.2 PDF 생성 방법

**Option A: HTML → PDF (추천)**
```python
# Weasyprint 또는 pdfkit 사용
from weasyprint import HTML

html_template = """
<html>
  <head>
    <meta charset="utf-8">
    <style>
      @font-face {
        font-family: 'Pretendard';
        src: url('fonts/Pretendard-Regular.woff2');
      }
      body { font-family: 'Pretendard', sans-serif; }
    </style>
  </head>
  <body>
    <h1>Share X 정산서 - 2025년 4분기</h1>
    <p>수신: {{ company_name }}</p>
    <table>
      <tr><td>매출액</td><td>{{ revenue | number_format }}</td></tr>
      <tr><td>정산 금액</td><td>{{ settlement | number_format }}</td></tr>
    </table>
  </body>
</html>
"""

HTML(string=html_template).write_pdf('output.pdf')
```

**Option B: ReportLab (Python 전용)**
```python
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 한글 폰트 등록
pdfmetrics.registerFont(TTFont('Pretendard', 'Pretendard-Regular.ttf'))

c = canvas.Canvas("output.pdf", pagesize=A4)
c.setFont('Pretendard', 12)
c.drawString(100, 750, "Share X 정산서 - 2025년 4분기")
c.save()
```

### 📤 출력
- `output/2025-Q4/쉐어엑스_ HEAZ 4Q 정산서.pdf`
- `output/2025-Q4/쉐어엑스_ BKID 4Q 정산서.pdf`
- ... (11개 기업)

### 🛠️ 구현 파일
- `src/mvp/pdf_generator.py`

### ✅ 검증
- 모든 기업별 PDF 생성 완료
- UTF-8 한글 정상 표시 (Windows/macOS 호환)
- 금액 표시 형식: 1,000,000원 (콤마 구분)

---

## 실행 방법

### CLI 명령어
```bash
# MVP 전체 파이프라인 실행
python3 scripts/run_mvp.py --period 2024-Q4

# 단계별 실행
python3 scripts/run_mvp.py --period 2024-Q4 --step extract
python3 scripts/run_mvp.py --period 2024-Q4 --step calculate
python3 scripts/run_mvp.py --period 2024-Q4 --step generate
```

### 파이프라인 플로우
```python
# scripts/run_mvp.py

def run_mvp_pipeline(period: str):
    # Step 1: PDF 추출
    pdf_path = f"archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - {period}.pdf"
    extracted_data = extract_pdf(pdf_path)
    save_json(extracted_data, f"output/{period}/intermediate_data.json")

    # Step 2: 안분 계산
    result = calculate_settlement(extracted_data)
    save_json(result, f"output/{period}/settlement_result.json")

    # Step 3: PDF 생성
    for company_id, data in result['companies'].items():
        generate_pdf(company_id, data, f"output/{period}/쉐어엑스_ {data['company_name']} 4Q 정산서.pdf")

    print(f"✅ MVP 파이프라인 완료: {period}")
```

---

## 검증 계획

### Phase 1: 2024 Q4 (확정 데이터)
```bash
python3 scripts/run_mvp.py --period 2024-Q4 --validate
```

**기대 결과**:
- 총 정산 금액: 32,708,346.5원 (±1원 이내)
- 각 기업별 금액이 `archive/Union_Profit Share_Settlement/` PDF와 일치

### Phase 2: 2025 Q4 (신규 데이터)
```bash
python3 scripts/run_mvp.py --period 2025-Q4
```

**기대 결과**:
- `output/2025-Q4_consolidated.json`의 수치와 일치
- 새로운 기업별 정산서 PDF 생성

---

## 의존성

### Python 패키지
```txt
# PDF 추출
PyPDF2==3.0.1
pdfplumber==0.10.3

# PDF 생성
weasyprint==60.1
reportlab==4.0.7

# 데이터 처리
pandas==2.1.4
openpyxl==3.1.2

# 기타
python-dateutil==2.8.2
```

### 시스템 요구사항
- Python 3.9+
- UTF-8 인코딩 지원
- 한글 폰트: Pretendard (크로스플랫폼)

---

## 파일 구조

```
ShareX_Settlement/
├── src/
│   └── mvp/
│       ├── __init__.py
│       ├── pdf_extractor.py      # Step 1
│       ├── settlement_calculator.py  # Step 2
│       └── pdf_generator.py      # Step 3
│
├── scripts/
│   └── run_mvp.py                # CLI 실행
│
├── output/
│   └── 2024-Q4/
│       ├── intermediate_data.json
│       ├── settlement_result.json
│       └── 쉐어엑스_ HEAZ 4Q 정산서.pdf
│
└── docs/
    └── MVP_PIPELINE.md           # 이 파일
```

---

## 향후 확장 (MVP 이후)

### Phase 2: 웹 UI
- 정산 결과 확인/수정 화면
- "확정" 버튼 → PDF 일괄 생성

### Phase 3: 자동 메일 발송
- 정산메일 템플릿 머지태그 치환
- Gmail/SendGrid API 연동

### Phase 4: 대시보드
- 분기별 정산 추이 차트
- 기업별 매출/정산 비교

---

## 참고 문서
- [CLAUDE.md](CLAUDE.md) - 프로젝트 전체 지침
- [README.md](../README.md) - 프로젝트 개요
