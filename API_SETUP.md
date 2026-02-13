# ShareX Settlement API 설정 및 실행 가이드

## 📌 문제: "분석 중" 상태에서 멈춤

웹 대시보드에서 정산서 업로드 후 **"분석 중"** 상태에서 응답이 없는 경우, API 서버가 실행 중이지 않기 때문입니다.

---

## ✅ 해결 방법 (2가지)

### 방법 1️⃣: **API 서버 실행** (웹 UI 사용 시)

```bash
# 터미널 1: FastAPI 백엔드 서버 시작
python3 scripts/run_api.py

# 터미널 2: Next.js 웹 대시보드 시작
cd web/dashboard
npm run dev

# 브라우저에서 접속
http://localhost:3000
```

**요구사항**:
- Python 3.8+
- FastAPI, Uvicorn 설치
- Next.js 환경

---

### 방법 2️⃣: **CLI 사용** (API 없이 직접 실행)

API 서버 없이 **CLI로 직접 정산을 실행**할 수 있습니다:

```bash
# 기본 실행 (PDF 추출 → 정산 계산 → PDF 생성)
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

**장점**:
- 별도 API 서버 불필요
- 빠른 실행 (의존성 최소화)
- CLI 친화적

---

## 📁 파일 위치

**입력**: `archive/FastCampus_Settlement/` (PDF 파일)
**출력**:
- `output/{YYYY-QN}/intermediate_data.json` (추출 데이터)
- `output/{YYYY-QN}/settlement_result.json` (정산 결과)
- `output/{YYYY-QN}/쉐어엑스_*.pdf` (정산서 12개)

---

## 🔧 API 서버 문제 해결

### API 서버가 실행 중이지만 "분석 중"에서 멈추는 경우

**1️⃣ PDF 파일명 확인**
```
✅ 올바른 형식: 2024년 4분기 정산서.pdf
❌ 잘못된 형식: settlement_2024.pdf
```

**2️⃣ 파일 위치 확인**
API 서버 log에서 에러 메시지 확인:
```bash
# 터미널에 출력되는 로그 확인
❌ PDF 파싱 실패: ...
```

**3️⃣ API 포트 충돌 확인**
```bash
# 포트 8000이 이미 사용 중이면:
lsof -i :8000
kill -9 <PID>

# 또는 다른 포트로 실행
uvicorn src.api.backend:app --host 0.0.0.0 --port 8001
```

---

## 🎯 권장 워크플로우

| 상황 | 추천 |
|------|------|
| **빠른 테스트** | CLI (`run_mvp.py`) |
| **웹 UI 필요** | API 서버 + 대시보드 |
| **배포** | Uvicorn + Gunicorn + NGINX |

---

## 📝 API 엔드포인트

### POST `/api/settlements/parse`
```bash
curl -X POST -F "file=@정산서.pdf" \
  http://localhost:8000/api/settlements/parse
```

**응답 (성공)**:
```json
{
  "period": "2024-Q4",
  "course_count": 37,
  "companies": {
    "plusx": { "settlement_amount": 111079669, ... },
    "huskyfox": { "settlement_amount": 6432849.5, ... }
  },
  "summary": { "total_settlement": 159250722 }
}
```

**응답 (실패)**:
```json
{
  "detail": "PDF 파싱 실패: 파일명에 'YYYY년 NQ' 형식이 필요합니다"
}
```

---

## 💡 팁

- **로그 확인**: API 터미널에서 `print()` 메시지 확인
- **캐시**: 브라우저 개발자도구 → Application → sessionStorage 확인
- **재시작**: 브라우저 새로고침 (Ctrl+R) 후 다시 시도

최종 업데이트: 2026-02-13
