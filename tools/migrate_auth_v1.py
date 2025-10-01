import os, sys, json, time, hmac, hashlib, base64, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))         # tools/
PROJ = os.path.abspath(os.path.join(ROOT, ".."))          # project root
BACKEND = os.path.join(PROJ, "backend")
FRONTEND = os.path.join(PROJ, "frontend")
ADMIN_HTML = os.path.join(FRONTEND, "admin", "index.html")
DATA = os.path.join(PROJ, "data")
AUTH_DIR = os.path.join(DATA, "auth")
SEED_DIR = os.path.join(DATA, "seed")

APP = os.path.join(BACKEND, "app.py")
UTILS = os.path.join(BACKEND, "utils.py")
AUTHX = os.path.join(BACKEND, "authx.py")     # new auth service
RBAC2 = os.path.join(BACKEND, "rbac2.py")     # new rbac/scopes
AUDIT = os.path.join(DATA, "audit.log")

os.makedirs(BACKEND, exist_ok=True)
os.makedirs(FRONTEND, exist_ok=True)
os.makedirs(os.path.join(FRONTEND, "admin"), exist_ok=True)
os.makedirs(SEED_DIR, exist_ok=True)
os.makedirs(AUTH_DIR, exist_ok=True)

USERS_JSON      = os.path.join(AUTH_DIR, "users.json")       # { email: {pwd_hash, salt, role, scope, created_at, locked, last_pw_change} }
REFRESH_JSON    = os.path.join(AUTH_DIR, "refresh.json")     # { token_id: {user, exp, ua_ip_hash, revoked} }
PASSWORD_BLACK  = os.path.join(AUTH_DIR, "blacklist.txt")    # optional blacklist
OPENAPI_NOTICE  = "===== v49 AUTHX & RBAC2 (appended) ====="

# ---------- utils.py (ensure load_json/save_json) ----------
if not os.path.exists(UTILS):
    with open(UTILS, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent("""
import os, json
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "seed")
def load_json(name: str):
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p): return {}
    with open(p, "r", encoding="utf-8") as f: return json.load(f)
def save_json(name: str, obj):
    p = os.path.join(DATA_DIR, name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)
"""))

# ---------- authx.py (auth service: signup/login/refresh/logout/whoami/setup) ----------
AUTHX_CODE = """
import os, json, time, hmac, hashlib, base64, random, string
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Dict, Any
from .utils import load_json, save_json

router = APIRouter()
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
AUTH_DIR = os.path.join(DATA_DIR, "auth")
USERS = os.path.join(AUTH_DIR, "users.json")
REFRESH = os.path.join(AUTH_DIR, "refresh.json")
BLACKLIST = os.path.join(AUTH_DIR, "blacklist.txt")

ACCESS_TTL = int(os.getenv("ACCESS_TTL_MINUTES", "15")) * 60
REFRESH_TTL = int(os.getenv("REFRESH_TTL_DAYS", "7")) * 24 * 3600
JWT_ISS = os.getenv("JWT_ISSUER", "visaready-auth")
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_now")  # set in env for prod
PASSWORD_MIN = 12

def _now(): return int(time.time())
def _b64(b:bytes): return base64.urlsafe_b64encode(b).decode().rstrip("=")
def _hmac(s:str): return hmac.new(JWT_SECRET.encode(), s.encode(), hashlib.sha256).digest()
def _sign(claims:Dict[str,Any]):
    body = json.dumps(claims, separators=(",",":"), sort_keys=True)
    return _b64(body.encode()) + "." + _b64(_hmac(body))

def _unsign(tok:str):
    try:
        b64, sig = tok.split(".")
        body = base64.urlsafe_b64decode(b64 + "==").decode()
        if _b64(_hmac(body)) != sig: raise ValueError("bad")
        payload = json.loads(body)
        if payload.get("exp",0) < _now(): raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(401, "invalid token")

def _load_users():
    if not os.path.exists(USERS): return {}
    with open(USERS,"r",encoding="utf-8") as f: return json.load(f)

def _save_users(d):
    os.makedirs(AUTH_DIR, exist_ok=True)
    with open(USERS,"w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)

def _load_refresh():
    if not os.path.exists(REFRESH): return {}
    with open(REFRESH,"r",encoding="utf-8") as f: return json.load(f)

def _save_refresh(d):
    os.makedirs(AUTH_DIR, exist_ok=True)
    with open(REFRESH,"w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)

def _pbkdf2(pwd:str, salt:bytes)->str:
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt, 200_000, dklen=32)
    return _b64(dk)

def _new_salt(): return os.urandom(16)

def _breach_check_local(pwd:str)->bool:
    # local blacklist check only (no outbound). You can add common passwords into blacklist.txt
    if os.path.exists(BLACKLIST):
        with open(BLACKLIST,"r",encoding="utf-8") as f:
            black = {line.strip() for line in f if line.strip()}
        if pwd.lower() in black: return True
    return False

def _ua_ip_hash(req:Request):
    ua = req.headers.get("user-agent","-")
    ip = req.client.host if req.client else "-"
    raw = (ua + "|" + ip).encode()
    return hashlib.sha256(raw).hexdigest()

def _mk_access(email:str, role:str, scope:dict):
    return _sign({"sub":email,"role":role,"scope":scope,"iss":JWT_ISS,"exp":_now()+ACCESS_TTL})

def _mk_refresh(email:str, ua_ip_hash:str):
    token_id = _b64(os.urandom(18))
    store = _load_refresh()
    store[token_id] = {"user": email, "ua": ua_ip_hash, "exp": _now()+REFRESH_TTL, "revoked": False}
    _save_refresh(store)
    return token_id

def _ensure_scope(role:str)->dict:
    # default scopes per role, can be adjusted later in admin UI
    defaults = {
        "super_admin": {"countries":[],"visa_types":[],"read_only": False},
        "compliance_admin":{"countries":[],"visa_types":[],"read_only": False},
        "content_admin":{"countries":[],"visa_types":[],"read_only": False},
        "support_admin":{"countries":[],"visa_types":[],"read_only": True},
        "marketing_admin":{"countries":[],"visa_types":[],"read_only": True},
        "data_admin":{"countries":[],"visa_types":[],"read_only": True},
        "user": {"countries":[],"visa_types":[],"read_only": True},
    }
    return defaults.get(role, {"countries":[],"visa_types":[],"read_only": True})

def _validate_password(pwd:str):
    if len(pwd) < PASSWORD_MIN: raise HTTPException(400, f"Password must be >= {PASSWORD_MIN} chars")
    if _breach_check_local(pwd): raise HTTPException(400, "Password too common")

@router.post("/auth/setup")
def setup(seed_email: str, seed_token: str):
    # One-time super admin bootstrap; disables itself by writing a marker
    marker = os.path.join(AUTH_DIR, ".setup_done")
    if os.path.exists(marker): raise HTTPException(403, "setup already done")
    expect_email = os.getenv("SUPERADMIN_SEED_EMAIL","").strip()
    expect_token = os.getenv("SUPERADMIN_SEED_TOKEN","").strip()
    if not expect_email or not expect_token: raise HTTPException(400, "seed envs not set")
    if seed_email.strip().lower()!=expect_email.lower() or seed_token.strip()!=expect_token.strip():
        raise HTTPException(401, "seed mismatch")

    users = _load_users()
    if seed_email in users: raise HTTPException(409, "already exists")
    salt = _new_salt()
    # we do not set a password here; super admin will set via /auth/signup_master
    users[seed_email] = {"pwd_hash": "", "salt": _b64(salt), "role":"super_admin", "scope": _ensure_scope("super_admin"),
                         "created_at": _now(), "locked": False, "last_pw_change": 0}
    _save_users(users)
    with open(marker,"w") as f: f.write("1")
    return {"ok": True}

@router.post("/auth/signup")    # user role
def signup(email: str, password: str):
    _validate_password(password)
    users = _load_users()
    if email in users and users[email]["pwd_hash"]: raise HTTPException(409, "account exists")
    salt = _new_salt()
    pwd_hash = _pbkdf2(password, salt)
    users[email] = {"pwd_hash": pwd_hash, "salt": _b64(salt), "role":"user", "scope": _ensure_scope("user"),
                    "created_at": _now(), "locked": False, "last_pw_change": _now()}
    _save_users(users)
    return {"ok": True}

@router.post("/auth/signup_master")  # set password for seeded superadmin
def signup_master(email: str, password: str):
    marker = os.path.join(AUTH_DIR, ".setup_done")
    if not os.path.exists(marker): raise HTTPException(403, "setup not initialised")
    _validate_password(password)
    users = _load_users()
    if email not in users: raise HTTPException(404, "no seed user")
    salt = _new_salt()
    users[email]["pwd_hash"] = _pbkdf2(password, salt)
    users[email]["salt"] = _b64(salt)
    users[email]["last_pw_change"] = _now()
    _save_users(users)
    return {"ok": True}

@router.post("/auth/login")
def login(request: Request, email: str, password: str):
    # rate limit: simple IP window 5/min (in-memory ephemeral)
    lim = RateLimiter.get(request.client.host)
    if not lim.allow(): raise HTTPException(429, "Too many attempts, try later")

    users = _load_users()
    u = users.get(email)
    if not u: raise HTTPException(401, "invalid")
    if u.get("locked"): raise HTTPException(401, "locked")
    salt = base64.urlsafe_b64decode((u["salt"]+"==").encode())
    if _pbkdf2(password, salt) != u["pwd_hash"]: raise HTTPException(401, "invalid")

    scope = u.get("scope") or _ensure_scope(u.get("role","user"))
    access = _mk_access(email, u.get("role","user"), scope)
    refresh_id = _mk_refresh(email, _ua_ip_hash(request))
    return {"access": access, "refresh": refresh_id, "role": u.get("role","user"), "scope": scope}

@router.post("/auth/refresh")
def refresh(request: Request, refresh: str):
    store = _load_refresh()
    rec = store.get(refresh)
    if not rec or rec.get("revoked"): raise HTTPException(401, "invalid refresh")
    if rec["exp"] < _now(): raise HTTPException(401, "expired")
    if rec["ua"] != _ua_ip_hash(request): raise HTTPException(401, "device mismatch")
    users = _load_users()
    u = users.get(rec["user"])
    if not u: raise HTTPException(401, "no user")
    scope = u.get("scope") or _ensure_scope(u.get("role","user"))
    access = _mk_access(rec["user"], u.get("role","user"), scope)
    # rotate refresh
    rec["revoked"] = True
    store[refresh] = rec
    new_id = _mk_refresh(rec["user"], rec["ua"])
    _save_refresh(store)
    return {"access": access, "refresh": new_id}

@router.post("/auth/logout")
def logout(refresh: str):
    store = _load_refresh()
    if refresh in store:
        store[refresh]["revoked"] = True
        _save_refresh(store)
    return {"ok": True}

@router.get("/auth/whoami")
def whoami(authorization: str | None = Header(default=None)):
    payload = _unsign(authorization.split(" ",1)[1]) if authorization and authorization.startswith("Bearer ") else {}
    return {"ok": True, "claims": payload}

# simple IP rate-limiter (5/min, burst 10)
class RateLimiter:
    BUCKET = {}
    CAP = 10
    WINDOW = 60
    @classmethod
    def get(cls, ip):
        if ip not in cls.BUCKET: cls.BUCKET[ip] = []
        return cls(ip)
    def __init__(self, ip): self.ip = ip
    def allow(self):
        now = _now()
        arr = self.BUCKET[self.ip] = [t for t in self.BUCKET.get(self.ip,[]) if now - t < self.WINDOW]
        if len(arr) >= self.CAP: return False
        arr.append(now); return True
"""

with open(AUTHX, "w", encoding="utf-8") as f:
    f.write(AUTHX_CODE)

# ---------- rbac2.py (roles, scopes, middleware helpers) ----------
RBAC2_CODE = """
from fastapi import HTTPException
def allow_write(route: str) -> bool:
    # whitelist write endpoints; deny by default
    return route in {
        "/admin/checklists:PUT",
        "/admin/duplicate:POST",
        "/admin/duplicate/bulk:POST",
        "/admin/validate/fix:POST",
        "/admin/import/csv:POST"
    }
def check_scope(role:str, scope:dict, key:str|None):
    if not key: return
    try:
        corr, purpose = key.split("::",1)
        origin, dest = corr.split("->",1)
    except Exception:
        raise HTTPException(400, "Bad key format")
    countries = (scope or {}).get("countries") or []
    visa_types = (scope or {}).get("visa_types") or []
    read_only = bool((scope or {}).get("read_only",False))
    if read_only: raise HTTPException(403, "Read-only role")
    if countries and (origin.upper() not in countries and dest.upper() not in countries):
        raise HTTPException(403, "Region not in scope")
    if visa_types and purpose.upper() not in visa_types:
        raise HTTPException(403, "Visa type not in scope")
"""

with open(RBAC2, "w", encoding="utf-8") as f:
    f.write(RBAC2_CODE)

# ---------- seed empty stores ----------
if not os.path.exists(USERS_JSON):
    with open(USERS_JSON, "w", encoding="utf-8") as f: json.dump({}, f)
if not os.path.exists(REFRESH_JSON):
    with open(REFRESH_JSON, "w", encoding="utf-8") as f: json.dump({}, f)
if not os.path.exists(PASSWORD_BLACK):
    with open(PASSWORD_BLACK, "w", encoding="utf-8") as f:
        f.write("password\n123456\nqwerty\nletmein\nvisaready\n")

# ---------- append to app.py: include auth router + RBAC middleware + audit ----------
if not os.path.exists(APP):
    print("ERROR: backend/app.py not found"); sys.exit(1)

with open(APP, "r", encoding="utf-8") as f:
    app_src = f.read()

if OPENAPI_NOTICE not in app_src:
    app_src += textwrap.dedent(f"""
# {OPENAPI_NOTICE}
try:
    from . import authx
except Exception:
    import authx
try:
    from . import rbac2
except Exception:
    import rbac2

from fastapi import Request, Header
import json as _json

app.include_router(authx.router)

@app.middleware("http")
async def auth_rbac_mw(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()
    route_key = f"{{path}}:{{method}}"
    guarded = rbac2.allow_write(route_key)
    claims = None
    key = None
    # attach claims to request.state if access token present (for header badge)
    authz = request.headers.get("authorization","")
    if authz.startswith("Bearer "):
        try:
            claims = authx._unsign(authz.split(" ",1)[1])
        except Exception:
            claims = None
    request.state.claims = claims

    if guarded:
        # parse payload to extract key if present
        body_bytes = await request.body()
        try:
            payload = _json.loads(body_bytes.decode() or "{{}}")
        except Exception:
            payload = {{}}
        key = payload.get("key") or payload.get("dst_key") or None
        if not claims:
            from fastapi import HTTPException
            raise HTTPException(401, "Missing/invalid access token")
        # scope checks
        rbac2.check_scope(claims.get("role",""), (claims.get("scope") or {{}}), key)
        async def receive():
            return {{"type": "http.request", "body": body_bytes}}
        request._receive = receive
    response = await call_next(request)
    return response
""")
    with open(APP, "w", encoding="utf-8") as f:
        f.write(app_src)

# ---------- inject Admin header (role + email) at runtime ----------
if os.path.exists(ADMIN_HTML):
    html = open(ADMIN_HTML, "r", encoding="utf-8").read()
    if "/* v-admin-header-badge */" not in html:
        # Ensure BACKEND const exists
        if "const BACKEND" not in html:
            html = html.replace("<script>", "<script>\\n  const BACKEND='http://127.0.0.1:8000';", 1)
        badge = r"""
<!-- v-admin header badge -->
<script>
/* v-admin-header-badge */
(function(){
  function ensureBadge(){
    const main = document.querySelector('main.container');
    if(!main) return;
    if (document.getElementById('adm_badge')) return;
    const bar = document.createElement('div');
    bar.id = 'adm_badge';
    bar.style.display='flex'; bar.style.justifyContent='space-between';
    bar.style.alignItems='center'; bar.style.margin='8px 0';
    bar.innerHTML = '<span class="small" id="adm_badge_text">—</span>';
    main.prepend(bar);
  }
  async function who(){
    try{
      const tok = window.token || window.VAL_TOKEN || '';
      if(!tok) { ensureBadge(); document.getElementById('adm_badge_text').textContent = 'Admin: (not signed)'; return; }
      const r = await fetch(`${BACKEND}/auth/whoami`, { headers: { 'Authorization': 'Bearer '+tok }});
      if(!r.ok){ ensureBadge(); document.getElementById('adm_badge_text').textContent = 'Admin: (token invalid)'; return; }
      const j = await r.json();
      const c = j.claims || {};
      ensureBadge();
      document.getElementById('adm_badge_text').textContent = `Admin: ${c.sub||'?'}  |  Role: ${c.role||'?'} `;
    }catch(e){
      ensureBadge();
      document.getElementById('adm_badge_text').textContent = 'Admin: (error)';
    }
  }
  document.addEventListener('DOMContentLoaded', who);
})();
</script>
"""
        html = html.replace("</body></html>", badge + "\n</body></html>")
        with open(ADMIN_HTML, "w", encoding="utf-8") as f:
            f.write(html)

print("AuthX + RBAC2 migration applied.")
print("Next:")
print(" 1) Set envs and restart backend:")
print('    $env:JWT_SECRET="change_me_now"; $env:ACCESS_TTL_MINUTES="15"; $env:REFRESH_TTL_DAYS="7"')
print('    $env:SUPERADMIN_SEED_EMAIL="you@example.com"; $env:SUPERADMIN_SEED_TOKEN="some-onetime-token"')
print("    python -m uvicorn backend.app:app --reload --port 8000")
print(" 2) Bootstrap super admin:")
print("    POST /auth/setup  body: {\"seed_email\":\"you@example.com\",\"seed_token\":\"some-onetime-token\"}")
print(" 3) Set super admin password:")
print("    POST /auth/signup_master  body: {\"email\":\"you@example.com\",\"password\":\"<NEW-STRONG-PASS>\"}")
print(" 4) Login (any portal):")
print("    POST /auth/login  {\"email\":\"you@example.com\",\"password\":\"...\"}")
print("    → returns {access, refresh, role, scope}")
print(" 5) Update your Admin UI login to store 'access' as token (window.token).")
