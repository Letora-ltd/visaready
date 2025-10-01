
# VisaReady — MVP v3

- Non-AI code, mobile-first, bright deep-blue + lime theme.
- PayPal Hosted Button integrated (payouts to Monzo via PayPal).
- Admin panel to edit checklists (login: password from `ADMIN_PASSWORD`, default `admin123`).
- Frontend fetches `/api/seed` first (live data), falls back to static `/frontend/seed` if backend is not running.

## Run backend
```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD="change_me"
uvicorn app:app --reload --port 8000
```

## Run frontend (static server)
```
cd frontend
python -m http.server 5173
open http://localhost:5173
```

## Admin panel
- Visit `http://localhost:5173/admin/`
- Login with your password (`ADMIN_PASSWORD`).
- Add/modify checklists via JSON editor. Keys are like `IN->TR::TOURIST`.

## Deploy
- Backend: Railway/Render (Start: `uvicorn app:app --host 0.0.0.0 --port 8000`)
- Frontend: Vercel/Netlify/Cloudflare Pages (static). For live updates, point frontend to backend domain (works automatically via `/api/seed`).

## Seeds
- 30 original corridors + 15 extra countries with IN<->Country corridors added.
- Sample checklists (GB->US::TOURIST, IN->GB::TOURIST, IN->TR::TOURIST) include official source links.
