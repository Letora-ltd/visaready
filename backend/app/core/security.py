import hmac, hashlib, base64, json, time
from fastapi import HTTPException, Header
from .config import settings

JWT_SECRET = "change_me_now"
ACCESS_TTL = 3600 * 24 # 1 day for dev simplicity

def _now(): return int(time.time())
def _b64(b:bytes): return base64.urlsafe_b64encode(b).decode().rstrip("=")

def sign_jwt(claims: dict):
    claims["exp"] = _now() + ACCESS_TTL
    body = json.dumps(claims, separators=(",",":"), sort_keys=True)
    raw = body.encode()
    sig = hmac.new(JWT_SECRET.encode(), raw, hashlib.sha256).digest()
    return _b64(raw) + "." + _b64(sig)

def decode_jwt(tok: str):
    try:
        b64, sig = tok.split(".")
        body = base64.urlsafe_b64decode(b64 + "==").decode()
        if _b64(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest()) != sig:
            raise ValueError("bad signature")
        payload = json.loads(body)
        if payload.get("exp", 0) < _now():
            raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_token")

def get_password_hash(password: str):
    # Simple hash for dev
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str):
    return get_password_hash(plain_password) == hashed_password
