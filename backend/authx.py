
import os, json, time, hmac, hashlib, base64, random, string
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Dict, Any
from pydantic import BaseModel

class SetupIn(BaseModel):
    body.seed_email: str
    body.seed_token: str

class SignupIn(BaseModel):
    email: str
    password: str

class SignupMasterIn(BaseModel):
    email: str
    password: str

class LoginIn(BaseModel):
    email: str
    password: str

class RefreshIn(BaseModel):
    

class LogoutIn(BaseModel):
    
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
def setup(body: SetupIn):
    # One-time super admin bootstrap; disables itself by writing a marker
    marker = os.path.join(AUTH_DIR, ".setup_done")
    if os.path.exists(marker): raise HTTPException(403, "setup already done")
    expect_email = os.getenv("SUPERADMIN_SEED_EMAIL","").strip()
    expect_token = os.getenv("SUPERADMIN_SEED_TOKEN","").strip()
    if not expect_email or not expect_token: raise HTTPException(400, "seed envs not set")
    if body.seed_email.strip().lower()!=expect_email.lower() or body.seed_token.strip()!=expect_token.strip():
        raise HTTPException(401, "seed mismatch")

    users = _load_users()
    if body.seed_email in users: raise HTTPException(409, "already exists")
    salt = _new_salt()
    # we do not set a password here; super admin will set via /auth/signup_master
    users[body.seed_email] = {"pwd_hash": "", "salt": _b64(salt), "role":"super_admin", "scope": _ensure_scope("super_admin"),
                         "created_at": _now(), "locked": False, "last_pw_change": 0}
    _save_users(users)
    with open(marker,"w") as f: f.write("1")
    return {"ok": True}

@router.post("/auth/signup")    # user role
def signup():
    _validate_password(body.password)
    users = _load_users()
    if email in users and users[email]["pwd_hash"]: raise HTTPException(409, "account exists")
    salt = _new_salt()
    pwd_hash = _pbkdf2(password, salt)
    users[email] = {"pwd_hash": pwd_hash, "salt": _b64(salt), "role":"user", "scope": _ensure_scope("user"),
                    "created_at": _now(), "locked": False, "last_pw_change": _now()}
    _save_users(users)
    return {"ok": True}

@router.post("/auth/signup_master")  # set password for seeded superadmin
def signup_master():
    marker = os.path.join(AUTH_DIR, ".setup_done")
    if not os.path.exists(marker): raise HTTPException(403, "setup not initialised")
    _validate_password(body.password)
    users = _load_users()
    if email not in users: raise HTTPException(404, "no seed user")
    salt = _new_salt()
    users[email]["pwd_hash"] = _pbkdf2(password, salt)
    users[email]["salt"] = _b64(salt)
    users[email]["last_pw_change"] = _now()
    _save_users(users)
    return {"ok": True}

@router.post("/auth/login")
def login(request: Request, body: LoginIn):
    # rate limit: simple IP window 5/min (in-memory ephemeral)
    lim = RateLimiter.get(request.client.host)
    if not lim.allow(): raise HTTPException(429, "Too many attempts, try later")

    users = _load_users()
    u = users.get(body.email)
    if not u: raise HTTPException(401, "invalid")
    if u.get("locked"): raise HTTPException(401, "locked")
    salt = base64.urlsafe_b64decode((u["salt"]+"==").encode())
    if _pbkdf2(body.password, salt) != u["pwd_hash"]: raise HTTPException(401, "invalid")

    scope = u.get("scope") or _ensure_scope(u.get("role","user"))
    access = _mk_access(body.email, u.get("role","user"), scope)
    refresh_id = _mk_refresh(body.email, _ua_ip_hash(request))
    return {"access": access, "refresh": refresh_id, "role": u.get("role","user"), "scope": scope}

@router.post("/auth/refresh")
def refresh(request: Request, body: RefreshIn):
    store = _load_refresh()
    rec = store.get(body.refresh)
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
    store[body.refresh] = rec
    new_id = _mk_refresh(rec["user"], rec["ua"])
    _save_refresh(store)
    return {"access": access, "refresh": new_id}

@router.post("/auth/logout")
def logout(body: LogoutIn):
    store = _load_refresh()
    if body.refresh in store:
        store[body.refresh]["revoked"] = True
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
