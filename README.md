# ShareX Settlement System

ShareX 정산 자동화 시스템 - 쉐어엑스 정산서 PDF를 파싱하여 기업별 정산서를 생성하고 관리합니다.

## 🎯 주요 기능

- ✅ PDF 업로드 및 자동 파싱 (0.34초)
- ✅ 기업별 정산 계산 (플러스엑스 비율 기간별 자동 적용: 70% → 65%)
- ✅ 웹 UI 정산서 상세 보기
- ✅ 교차검증 모델 (데이터 일관성 체크)
- ✅ Remarks 입력 및 저장
- ✅ 아카이브 저장 (로컬 JSON)
- ✅ 백그라운드 PDF 생성

## 🏗️ 기술 스택

### Backend
- **FastAPI** - Python 3.12+
- **pdfplumber** - PDF 파싱
- **uvicorn** - ASGI 서버

### Frontend
- **Next.js 16** - React 19
- **Tailwind CSS v4** - 스타일링
- **TypeScript** - 타입 안정성

## 📦 프로젝트 구조

```
ShareX_Settlement/
├── src/
│   ├── api/
│   │   └── backend.py              # FastAPI 서버
│   ├── mvp/
│   │   ├── pdf_extractor.py        # PDF 데이터 추출
│   │   ├── settlement_calculator.py # 정산 계산
│   │   └── pdf_generator.py        # PDF 생성
│   └── parsers/
│       └── fastcampus_pdf.py       # FastCampus PDF 파서
├── web/
│   └── dashboard/
│       ├── src/
│       │   ├── app/
│       │   │   └── projects/settlement/
│       │   │       ├── page.tsx           # 정산 리스트
│       │   │       └── [id]/page.tsx      # 정산 상세
│       │   └── lib/
│       │       ├── api.ts                 # API 클라이언트
│       │       └── format.ts              # 포맷 유틸리티
│       └── package.json
├── data/
│   ├── companies.json              # 기업 정보 (계약조건, 계좌 등)
│   └── archive/                    # 저장된 정산 데이터 (JSON)
├── scripts/
│   └── run_mvp.py                  # CLI 실행 스크립트
└── docs/
    └── SERVICE_PROTOCOL.md         # 완전한 서비스 프로토콜
```

## 🚀 로컬 개발 환경 설정

### 1. Python 백엔드 설정

```bash
# Python 3.12 이상 필요
python3 --version

# 의존성 설치
pip install -r requirements.txt

# FastAPI 서버 실행
python3 -m uvicorn src.api.backend:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 http://localhost:8000/docs 에서 API 문서를 확인할 수 있습니다.

### 2. Next.js 프론트엔드 설정

```bash
cd web/dashboard

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

웹 UI는 http://localhost:3000 에서 접근할 수 있습니다.

### 3. 환경 변수 설정

프론트엔드 `.env.local` 파일 생성:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📖 사용 방법

### 웹 UI 사용

1. http://localhost:3000/projects/settlement 접속
2. "정산서 업로드" 버튼 클릭하여 FastCampus PDF 업로드
3. 파싱된 기업별 정산 내역 확인
4. 각 기업의 "상세" 버튼 클릭하여 강의별 내역 확인
5. Remarks 입력 및 "임시 저장"
6. 교차검증 결과 확인
7. "최종 승인" 클릭하여 아카이브 저장 및 PDF 생성

### CLI 사용 (선택사항)

```bash
# 기본 실행 (분기 PDF 파싱)
python3 scripts/run_mvp.py --period 2024-Q4

# 검증 모드 (교차검증 포함)
python3 scripts/run_mvp.py --period 2024-Q4 --validate

# 월별 데이터 포함 (향후 지원)
python3 scripts/run_mvp.py --period 2024-Q4 --monthly
```

## 🌐 배포

### Vercel (프론트엔드)

```bash
cd web/dashboard
vercel deploy
```

환경 변수 설정:
- `NEXT_PUBLIC_API_URL`: FastAPI 백엔드 URL (예: https://your-backend.railway.app)

### Railway/Render (백엔드)

**Railway:**
```bash
# railway.toml 생성
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn src.api.backend:app --host 0.0.0.0 --port $PORT"
```

**Render:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn src.api.backend:app --host 0.0.0.0 --port $PORT`

### 데이터베이스 마이그레이션

현재는 로컬 JSON 파일로 저장하지만, 프로덕션 배포 시 다음 중 선택:

**Supabase (PostgreSQL + Storage):**
```sql
CREATE TABLE settlements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period VARCHAR(10) NOT NULL,
  company_id VARCHAR(50) NOT NULL,
  settlement_amount DECIMAL NOT NULL,
  approved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**Vercel Postgres:**
```bash
npm install @vercel/postgres
```

자세한 내용은 [SERVICE_PROTOCOL.md](docs/SERVICE_PROTOCOL.md)의 Phase 6 참조.

## 📊 데이터 구조

### Archive JSON 형식

```json
{
  "period": "2025-Q1",
  "saved_at": "2025-02-12T15:30:00",
  "companies": {
    "plusx": {
      "company_name": "플러스엑스",
      "revenue": 149773988,
      "settlement_amount": 104841792,
      "union_payout_ratio": 0.70,
      "courses": [...]
    }
  },
  "summary": {
    "total_revenue": 149773988,
    "total_settlement": 104841792
  },
  "remarks": {
    "plusx": "정산 확인 완료"
  }
}
```

## 🔧 트러블슈팅

### API 연결 실패 (ERR_CONNECTION_REFUSED)

```bash
# FastAPI 서버 실행 여부 확인
curl http://localhost:8000/health

# 서버 재시작
python3 -m uvicorn src.api.backend:app --host 0.0.0.0 --port 8000 --reload
```

### Archive API 404 에러

서버 재시작이 필요할 수 있습니다. FastAPI의 `--reload` 옵션을 사용하면 코드 변경 시 자동 재시작됩니다.

### PDF 파싱 실패

- 지원 형식: 2024-Q4, 2025-Q1 양식
- 2025-Q4 신규 양식은 Phase 4에서 지원 예정

## 📋 개발 로드맵

자세한 내용은 [SERVICE_PROTOCOL.md](docs/SERVICE_PROTOCOL.md) 참조.

### 🔥 Critical (즉시 필요)
1. 승인 상태 추적 (Phase 2.1)
2. 아카이브 목록 페이지 (Phase 2.3)
3. PDF 다운로드 링크 제공 (Phase 2.2)

### 🚀 High (1-2주 내)
4. 새 PDF 양식 파서 (Phase 4)
5. 이메일 발송 자동화 (Phase 3)

### 📊 Medium (1-2개월)
6. 대시보드 및 분석 (Phase 5)
7. DB 마이그레이션 (Phase 6)

### 🔐 Low (향후)
8. 사용자 인증 및 권한 (Phase 7)

## 🤝 기여

버그 리포트 및 기능 제안은 Issues에 등록해주세요.

## 📄 라이센스

Copyright (c) 2025 PlusX. All rights reserved.

---

**개발**: PlusX Team
**프로젝트 시작**: 2025년 2월
**현재 버전**: MVP 1.0.0
