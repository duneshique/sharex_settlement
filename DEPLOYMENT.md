# 배포 가이드

ShareX Settlement 시스템을 프로덕션 환경에 배포하기 위한 단계별 가이드입니다.

## 📋 배포 아키텍처

```
┌─────────────────────────────────────┐
│        Vercel (프론트엔드)          │
│     Next.js 16 + React 19           │
│    (http://your-domain.com)         │
└────────────────┬────────────────────┘
                 │
                 ↓ API 호출
                 │
┌─────────────────────────────────────┐
│       Railway/Render (백엔드)       │
│    FastAPI + Python 3.12            │
│  (https://api.your-domain.com)      │
└────────────────┬────────────────────┘
                 │
                 ↓ 데이터 저장
                 │
┌─────────────────────────────────────┐
│    Supabase (DB + 파일 스토리지)    │
│  PostgreSQL + Storage (PDF, JSON)   │
└─────────────────────────────────────┘
```

## 🚀 1단계: GitHub에 푸시

### 1.1 GitHub 저장소 설정

```bash
cd /Users/plusx-junsikhwang/Documents/GitHub/ShareX_Settlement

# 기존 저장소 확인
git remote -v

# 원격 저장소 추가 (필요한 경우)
git remote add origin https://github.com/duneshique/ShareX_Settlement.git
```

### 1.2 코드 푸시

```bash
git add .
git commit -m "feat: MVP 1.0.0 배포 준비 완료

- 정산서 PDF 파싱 및 자동 계산
- 웹 UI 구현 (리스트, 상세 보기)
- 교차검증 모델 및 Remarks 저장
- Archive API 구현
- .gitignore, README, vercel.json 설정"

git push -u origin main
```

---

## 🌐 2단계: Vercel에 프론트엔드 배포

### 2.1 Vercel CLI 설치

```bash
npm i -g vercel
```

### 2.2 프론트엔드 배포

```bash
cd web/dashboard
vercel deploy --prod
```

배포 중 물어보는 항목들:

```
? Set up and deploy "~/ShareX_Settlement/web/dashboard"? [Y/n] Y
? Which scope do you want to deploy to? [account-name]
? Link to existing project? [y/N] N
? What's your project's name? sharex-settlement
? In which directory is your code located? ./
? Want to modify these settings before deploying? [y/N] N
```

**배포 후 정보:**
- 프론트엔드 URL: `https://sharex-settlement.vercel.app`
- 환경 변수 설정 필요

### 2.3 Vercel 환경 변수 설정

Vercel 대시보드 → Settings → Environment Variables

```
NEXT_PUBLIC_API_URL = https://your-backend-api.com
```

---

## 🔧 3단계: Railway에 백엔드 배포

### 3.1 Railway 가입 및 프로젝트 생성

https://railway.app 접속 → GitHub 로그인

### 3.2 Python 백엔드 배포

```bash
# Railway CLI 설치
npm i -g @railway/cli

# 로그인
railway login

# 프로젝트 생성 및 배포
cd /Users/plusx-junsikhwang/Documents/GitHub/ShareX_Settlement
railway init
railway up
```

### 3.3 Railway railway.toml 설정

`railway.toml` 파일 생성:

```toml
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn src.api.backend:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 5
```

### 3.4 환경 변수 설정

Railway 대시보드 → Variables

```
DATABASE_URL=postgresql://...  (Supabase에서 복사)
STORAGE_URL=https://...         (Supabase에서 복사)
```

---

## 📊 4단계: Supabase 데이터베이스 설정 (선택사항)

현재는 로컬 JSON으로 저장 중입니다. 프로덕션 배포 시:

### 4.1 Supabase 가입

https://supabase.com → 신규 프로젝트 생성

### 4.2 테이블 생성

```sql
-- Settlements 테이블
CREATE TABLE settlements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period VARCHAR(10) NOT NULL,
  company_id VARCHAR(50) NOT NULL,
  company_name VARCHAR(100),
  revenue DECIMAL(15, 2),
  settlement_amount DECIMAL(15, 2),
  union_payout_ratio DECIMAL(5, 2),
  approved BOOLEAN DEFAULT FALSE,
  remarks TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Archive 테이블
CREATE TABLE archives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period VARCHAR(10) NOT NULL UNIQUE,
  data JSONB,
  saved_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.3 파일 스토리지 생성

Supabase → Storage → Create New Bucket

- Bucket name: `settlements`
- Public: ❌ Private

---

## 🧪 5단계: 배포 후 테스트

### 5.1 프론트엔드 테스트

```bash
# 배포된 URL 접속
https://sharex-settlement.vercel.app/projects/settlement

# 확인 사항:
# ✅ 페이지 로딩 확인
# ✅ API 응답 확인 (브라우저 DevTools → Network)
# ✅ 정산서 업로드 테스트
```

### 5.2 백엔드 테스트

```bash
# API 문서
https://your-backend-api.com/docs

# 헬스 체크
curl https://your-backend-api.com/health

# 환경 변수 확인
curl https://your-backend-api.com/config
```

### 5.3 데이터베이스 테스트

```bash
# Supabase SQL Editor에서 쿼리 실행
SELECT * FROM settlements LIMIT 1;
SELECT * FROM archives LIMIT 1;
```

---

## 🔑 환경 변수 정리

### 프론트엔드 (Vercel)

```env
# .env.production (배포 환경)
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

### 백엔드 (Railway)

```env
# .env (로컬 테스트)
DATABASE_URL=postgresql://user:password@host:5432/dbname
STORAGE_URL=https://xxx.supabase.co/storage/v1/object/public/settlements
STORAGE_KEY=your-supabase-key
```

---

## 💡 배포 최적화 팁

### 1. 백엔드 성능 최적화

```python
# src/api/backend.py
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sharex-settlement.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. 프론트엔드 성능 최적화

```typescript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  compress: true,
  poweredByHeader: false,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
```

### 3. 무한 로드 방지

```typescript
// lib/api.ts
const TIMEOUT = 10000; // 10초 타임아웃

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {}
) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}
```

---

## 🐛 배포 후 문제 해결

### "API 연결 실패" (ERR_CONNECTION_REFUSED)

```bash
# Railway 로그 확인
railway logs

# 백엔드 상태 확인
curl https://your-backend-api.com/health

# Vercel 환경 변수 재확인
vercel env ls
```

### "CORS 에러"

Railway `railway.toml`에서 CORS 설정 확인:

```python
# src/api/backend.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sharex-settlement.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### "데이터베이스 연결 실패"

```bash
# Railway 환경 변수 확인
railway variables

# Supabase 연결 문자열 재확인
# PostgreSQL 포트: 5432 (Railway의 경우 자동 할당)
```

---

## 📝 배포 체크리스트

- [ ] GitHub 저장소 생성 및 코드 푸시
- [ ] Vercel 프로젝트 생성 및 배포
- [ ] Railway 프로젝트 생성 및 백엔드 배포
- [ ] Supabase 프로젝트 생성 (선택사항)
- [ ] 환경 변수 설정 (Vercel + Railway)
- [ ] 프론트엔드 배포 확인
- [ ] 백엔드 API 테스트 (`/health`, `/docs`)
- [ ] 통합 테스트 (웹 UI에서 PDF 업로드)
- [ ] 데이터베이스 연결 확인
- [ ] 모니터링 설정 (선택사항)

---

## 📞 지원

배포 중 문제가 발생하면:

1. **Vercel 문서**: https://vercel.com/docs
2. **Railway 문서**: https://docs.railway.app
3. **Supabase 문서**: https://supabase.com/docs
4. **FastAPI 문서**: https://fastapi.tiangolo.com
5. **Next.js 문서**: https://nextjs.org/docs

---

**마지막 업데이트**: 2025년 2월 13일
**버전**: MVP 1.0.0
