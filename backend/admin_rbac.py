
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
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
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
