# Deploying Vixa to `vixaa.online` (GoDaddy domain)

This project is split into:
- **Frontend** static site (`frontend/`)
- **Backend API** FastAPI (`backend/`)

Recommended production setup:
- Frontend on **Vercel**
- Backend on **Render**
- Domain DNS managed in **GoDaddy**

## 1) Deploy backend API (Render)
1. Push this repository to GitHub.
2. In Render, create a **Blueprint** deploy and point to `render.yaml`.
3. Confirm env vars:
   - `ADMIN_PASSWORD` (auto-generated)
   - `CORS_ORIGINS=https://vixaa.online,https://www.vixaa.online`
4. Deploy.
5. Copy backend URL, e.g. `https://vixaa-api.onrender.com`.

## 2) Point frontend to backend URL
In `frontend/index.html`, API currently defaults to `http://localhost:8000` only on localhost and same-origin in prod.

For split-host production, add this before deploy:
- `const API = 'https://vixaa-api.onrender.com';`

(Or move frontend behind same domain reverse proxy later.)

## 3) Deploy frontend (Vercel)
1. In Vercel, import this repo.
2. Set **Root Directory** to `frontend`.
3. Build command: none.
4. Output directory: `.`
5. Deploy and copy generated Vercel domain.

## 4) Configure GoDaddy DNS for `vixaa.online`
In GoDaddy DNS:
- `@` A record → `76.76.21.21` (Vercel apex IP)
- `www` CNAME → `cname.vercel-dns.com`

Then in Vercel project domains:
- Add `vixaa.online`
- Add `www.vixaa.online`

## 5) SSL and verification
- Vercel provisions SSL automatically after DNS propagation.
- Verify:
  - `https://vixaa.online`
  - `https://www.vixaa.online`
  - Frontend requests to backend succeed (CORS configured).

## 6) Production checklist
- Change admin password to a strong secret.
- Replace JSON storage with managed DB before scale.
- Add uptime monitoring for frontend and backend.
- Add error tracking (Sentry) and API logging.
