# Cloudflare Pages Deployment Guide for ShareX Settlement

이 가이드는 **ShareX Settlement Dashboard**를 Cloudflare Pages에 배포하기 위한 설정 단계입니다.

## 1. Cloudflare Pages 설정
Cloudflare 대시보드에서 `Pages` -> `Create a project` -> `Connect to Git`을 선택합니다.

### Build Settings
*   **Project name**: `sharex-settlement`
*   **Production branch**: `main`
*   **Framework preset**: `Next.js`
*   **Root directory**: `/web/dashboard`
*   **Build command**: `npm run build`
*   **Output directory**: `.next`

## 2. Environment Variables (환경 변수)
배포 시 `Settings` -> `Environment variables`에서 다음을 추가해야 합니다.

| Variable | Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://your-railway-api-url.up.railway.app` | Railway에 배포된 백엔드 API 주소 |
| `NODE_VERSION` | `20` (또는 최신 LTS) | 빌드 시 사용할 Node.js 버전 |

## 3. 백엔드 배포 (Railway 추천)
프론트엔드와 통신하기 위해 백엔드 API도 함께 배포되어야 합니다.
*   **Tool**: [Railway](https://railway.app/)
*   **Config**: 루트에 있는 `railway.toml`이 자동으로 설정값을 잡아줍니다.
*   **Command**: `uvicorn src.api.backend:app --host 0.0.0.0 --port $PORT`

## 4. Supabase 연동 (Optional - 향후 기획 단계)
데이터 영구 저장을 위해 Supabase URL과 Key를 백엔드 환경변수에 등록하면 모든 정산 내역이 클라우드에 보관됩니다.
