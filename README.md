# Vixa Platform

Production-minded visa-tech starter platform for India/UK outbound travelers.

## Stack
- **Backend:** FastAPI (Python), JSON persistence for local/dev, REST APIs.
- **Frontend:** Static HTML/CSS/JS app with responsive UX and API integration.
- **Data:** Seeded corridor/checklist datasets under `data/seed`.

## Implemented capabilities
- Public landing + visa discovery search
- User signup/login + authenticated session token
- Application draft creation + submission status updates
- Document vault behavior (attach document names per application)
- Payment-ready architecture (`/api/payments/intent` mock adapter)
- Tracking dashboard for user applications
- Legal + security pages
- Admin checklist tooling preserved from existing repo

## Run locally
### 1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload --port 8000
```

### 2) Frontend
```bash
cd frontend
python -m http.server 5173
```
Open `http://localhost:5173`.

## Core APIs
- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me`
- `GET /api/visas/search`
- `GET /api/visas/{origin}/{dest}`
- `POST /api/applications`
- `GET /api/applications`
- `POST /api/applications/{app_id}/submit`
- `POST /api/documents/upload`
- `POST /api/payments/intent`

## Notes for production hardening
- Replace JSON file persistence with PostgreSQL.
- Replace in-memory sessions with signed JWT + refresh token table/redis.
- Integrate payment gateway (Stripe/Razorpay) into payment intent adapter.
- Add object storage (S3/GCS) for actual binary document uploads.
- Configure reverse proxy + TLS + WAF and structured logging exports.
