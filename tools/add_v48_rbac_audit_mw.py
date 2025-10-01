import os, sys, json, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))  # tools/
PROJ = os.path.abspath(os.path.join(ROOT, ".."))   # project root
BACKEND = os.path.join(PROJ, "backend")
DATA = os.path.join(PROJ, "data")
SEED = os.path.join(DATA, "seed")

APP = os.path.join(BACKEND, "app.py")
UTILS = os.path.join(BACKEND, "utils.py")
RBAC = os.path.join(BACKEND, "admin_rbac.py")
USERS = os.path.join(SEED, "admin_users.json")

os.makedirs(BACKEND, exist_ok=True)
os.makedirs(SEED, exist_ok=True)

# ---------- admin_rbac.py ----------
rbac_code = textwrap.dedent("""
import os, json, time, hmac, hashlib, base64
from typing import Dict, Any, List
from fastapi import HTTPException, Request

USERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seed", "admin_users.json")
AUDIT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "audit.log")

ADMIN_SECRET = os.getenv("ADMIN_SECRET", os.getenv("ADMIN_PASSWORD", "admin123"))

def _now() -> int: return int(time.time())
def _b64(b: bytes) -> str: return base64.urlsafe_b64encode(b).decode().rstrip("=")
def _hmac(s: str) -> str: return _b64(hmac.new(ADMIN_SECRET.encode(), s.encode(), hashlib.sha256).digest())

def sign(claims: Dict[str, Any]) -> str:
    body = json.dumps(claims, separators=(",", ":"), sort_keys=True)
    sig = _hmac(body)
    return _b64(body.encode()) + "." + sig

def unsign(tok: str) -> Dict[str, Any]:
    try:
        body_b64, sig = tok.split(".")
        body = base64.urlsafe_b64decode(body_b64 + "==").decode()
        if _hmac(body) != sig: raise ValueError("bad sig")
        return json.loads(body)
    except Exception:
        raise HTTPException(401, "Token invalid")

def load_users() -> Dict[str, Any]:
    if not os.path.exists(USERS_PATH): return {}
    with open(USERS_PATH, "r", encoding="utf-8") as f: return json.load(f)

def save_users(obj: Dict[str, Any]):
    with open(USERS_PATH, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2, ensure_ascii=False)

def issue_token(username: str, read_only: bool, regions: List[str], visa_types: List[str], ttl_hours: int = 24) -> str:
    exp = _now() + ttl_hours*3600
    claims = {"sub": username, "ro": bool(read_only), "regions": [r.upper() for r in regions or []],
              "visa": [v.upper() for v in visa_types or []], "exp": exp}
    return sign(claims)

def verify_authz(authorization: str | None) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    tok = authorization.split(" ", 1)[1]
    claims = unsign(tok)
    if _now() >= int(claims.get("exp", 0)):
        raise HTTPException(401, "Token expired")
    return claims

def check_write(claims: Dict[str, Any]):
    if claims.get("ro"): raise HTTPException(403, "Read-only admin")

def corridor_allowed(claims: Dict[str, Any], key: str):
    # key: ORIGIN->DEST::PURPOSE
    try:
        corr, purpose = key.split("::", 1)
        origin, dest = corr.split("->", 1)
    except Exception:
        raise HTTPException(400, "Bad key format")
    regions = claims.get("regions") or []
    visa = claims.get("visa") or []
    if regions and (origin.upper() not in regions and dest.upper() not in regions):
        raise HTTPException(403, f"Region scope denied for {origin}->{dest}")
    if visa and purpose.upper() not in visa:
        raise HTTPException(403, f"Visa-type scope denied for {purpose}")

def audit(request: Request, user: str, action: str, key: str | None, ok: bool, reason: str | None = None):
    try:
        line = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ip": request.client.host if request and request.client else "-",
            "user": user or "-",
            "action": action, "key": key, "ok": ok,
            "reason": (reason or ""), "path": request.url.path if request else "-"
        }
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\\n")
    except Exception:
        pass

def create_user(master_password: str, username: str, read_only: bool, regions: list[str], visa_types: list[str], expires_at: str | None):
    if master_password != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(401, "Master password invalid")
    u = load_users()
    u[username] = {
        "read_only": bool(read_only),
        "regions": [r.upper() for r in (regions or [])],
        "visa_types": [v.upper() for v in (visa_types or [])],
        "expires_at": (expires_at or "").strip()
    }
    save_users(u)
    return {"ok": True, "user": username}

def login(username: str, password: str, ttl_hours: int = 24) -> str:
    if password != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(401, "Password invalid")
    users = load_users()
    if username not in users: raise HTTPException(401, "Unknown admin user")
    u = users[username]
    exp = (u.get("expires_at") or "").strip()
    if exp:
        try:
            y, m, d = map(int, exp.split("-"))
            # expiry at end of day local (simple)
            if time.time() > time.mktime((y, m, d, 23, 59, 59, 0, 0, -1)):
                raise HTTPException(401, "Account expired")
        except Exception:
            raise HTTPException(400, "Bad expires_at (YYYY-MM-DD)")
    return issue_token(username, u.get("read_only", False), u.get("regions") or [], u.get("visa_types") or [], ttl_hours)
""")

open(RBAC, "w", encoding="utf-8").write(rbac_code)

# ---------- utils.py (ensure load_json/save_json) ----------
if not os.path.exists(UTILS):
    open(UTILS, "w", encoding="utf-8").write(textwrap.dedent("""
import os, json
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "seed")
def load_json(name: str):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)
def save_json(name: str, obj):
    tmp = os.path.join(DATA_DIR, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, os.path.join(DATA_DIR, name))
"""))

# ---------- seed admin_users.json ----------
if not os.path.exists(USERS):
    with open(USERS, "w", encoding="utf-8") as f:
        json.dump({"superadmin": {"read_only": False, "regions": [], "visa_types": [], "expires_at": ""}}, f, indent=2, ensure_ascii=False)

# ---------- patch app.py by appending middleware + user mgmt ----------
if not os.path.exists(APP):
    print("ERROR: backend/app.py not found")
    sys.exit(1)

app_src = open(APP, "r", encoding="utf-8").read()

append_block = textwrap.dedent("""
# ===== v48 RBAC & Audit (appended) =====
try:
    from . import admin_rbac
except Exception:
    import admin_rbac
from fastapi import Request, Header, HTTPException
import json as _json

class CreateUserIn(BaseModel):
    master_password: str
    username: str
    read_only: bool = False
    regions: list[str] = []
    visa_types: list[str] = []
    expires_at: str | None = ""

@app.post("/admin/users")
def admin_create_user(payload: CreateUserIn):
    return admin_rbac.create_user(payload.master_password, payload.username, payload.read_only, payload.regions, payload.visa_types, payload.expires_at or "")

# Optional: username-based login (keeps original /admin/login working)
class Login2In(BaseModel):
    username: str
    password: str

@app.post("/admin/login2")
def admin_login2(payload: Login2In):
    token = admin_rbac.login(payload.username, payload.password, ttl_hours=24)
    return {"token": token}

@app.middleware("http")
async def rbac_guard(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()
    guarded = (
        (path == "/admin/checklists" and method == "PUT") or
        (path == "/admin/duplicate" and method == "POST") or
        (path == "/admin/duplicate/bulk" and method == "POST") or
        (path == "/admin/validate/fix" and method == "POST") or
        (path == "/admin/import/csv" and method == "POST")
    )
    claims = None
    key = None
    ok = True
    if guarded:
        try:
            claims = admin_rbac.verify_authz(request.headers.get("authorization"))
            admin_rbac.check_write(claims)
            # Best effort: parse body to enforce region/visa if 'key' or dst_key present
            body_bytes = await request.body()
            try:
                payload = _json.loads(body_bytes.decode() or "{}")
            except Exception:
                payload = {}
            if path == "/admin/checklists":
                key = payload.get("key")
            elif path == "/admin/duplicate":
                key = payload.get("dst_key")
            if key:
                admin_rbac.corridor_allowed(claims, key)
            # Re-inject body for downstream (Starlette trick)
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
        except HTTPException as e:
            ok = False
            admin_rbac.audit(request, (claims or {}).get("sub","-") if claims else "-", f"{method} {path}", key, False, request.headers.get("X-Reason"))
            raise
        except Exception:
            ok = False
            admin_rbac.audit(request, (claims or {}).get("sub","-") if claims else "-", f"{method} {path}", key, False, request.headers.get("X-Reason"))
            raise
    response = await call_next(request)
    # Audit successful writes
    if guarded and ok:
        admin_rbac.audit(request, (claims or {}).get("sub","-") if claims else "-", f"{method} {path}", key, True, request.headers.get("X-Reason"))
    return response
# ===== end v48 =====
""")

if "===== v48 RBAC & Audit (appended) =====" not in app_src:
    with open(APP, "a", encoding="utf-8") as f:
        f.write("\n" + append_block)

print("RBAC + audit middleware appended.")
print("Files written:")
print(" - backend/admin_rbac.py")
print(" - backend/utils.py (ensured)")
print(" - data/seed/admin_users.json (ensured)")
print(" - backend/app.py (middleware appended)")
