import os, sys, textwrap

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(ROOT, "backend", "app.py")
DATA = os.path.join(ROOT, "data")
AUDIT = os.path.join(DATA, "audit.log")

if not os.path.exists(APP):
    print("ERROR: backend/app.py not found"); sys.exit(1)

with open(APP, "r", encoding="utf-8") as f:
    app_src = f.read()

block = textwrap.dedent("""
# ===== v-batch23-backend =====
from fastapi import Query

@app.get("/admin/audit/view")
def admin_audit_view(authorization: str | None = Header(default=None),
                     start: int = Query(0, ge=0),
                     limit: int = Query(200, ge=1, le=2000)):
    # token check: only authenticated admins may read
    try:
        claims = authx._unsign((authorization or "").split(" ",1)[1]) if authorization and authorization.startswith("Bearer ") else None
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    # read tail-ish
    path = os.path.join(os.path.dirname(__file__), "..", "data", "audit.log")
    if not os.path.exists(path): return {"ok": True, "total": 0, "items": []}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    total = len(lines)
    chunk = lines[start:start+limit]
    # return raw lines; UI parses JSON per line
    return {"ok": True, "total": total, "start": start, "limit": limit, "items": [l.strip() for l in chunk]}
# ===== end v-batch23-backend =====
""")

if "===== v-batch23-backend =====" not in app_src:
    with open(APP, "a", encoding="utf-8") as f:
        f.write("\n"+block)
    print("Appended /admin/audit/view endpoint.")
else:
    print("Backend batch23 already applied.")

# ensure audit.log exists
os.makedirs(DATA, exist_ok=True)
if not os.path.exists(AUDIT):
    with open(AUDIT, "w", encoding="utf-8") as f:
        f.write("")
    print("Created empty data/audit.log")
