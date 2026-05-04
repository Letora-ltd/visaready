# Vixa

Vixa is a visa-tech web application with a modern UX, realtime slot visibility simulation, account management, and an end-to-end visa application flow.

## Highlights
- Visa corridor discovery by origin country (IN/GB focus)
- Realtime slot availability API (deterministic daily simulation for local/dev)
- Account signup/login with session auth
- Multi-step application wizard (draft → documents → payment intent → submit)
- User dashboard with status tracking
- Legal pages and security page

## Local run
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

```bash
cd frontend
python -m http.server 5173
```

Then open http://localhost:5173

## Key APIs
- `GET /api/visas/search`
- `GET /api/visas/{origin}/{dest}`
- `GET /api/slots/realtime?origin=IN&dest=AE`
- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me`
- `POST /api/applications`
- `GET /api/applications`
- `POST /api/documents/upload`
- `POST /api/payments/intent`
- `POST /api/applications/{app_id}/submit`

## Notes
- Slot availability is simulated but shaped as a production API contract.
- Document upload currently stores metadata only for dev portability.

## Production deployment
See `DEPLOYMENT.md` for GoDaddy domain setup (`vixaa.online`) with Vercel + Render.
