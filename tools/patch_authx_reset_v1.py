import os, sys, textwrap, json, time, base64, hashlib, hmac

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUTHX = os.path.join(ROOT, "backend", "authx.py")
if not os.path.exists(AUTHX):
    print("ERROR: backend/authx.py not found"); sys.exit(1)

src = open(AUTHX, "r", encoding="utf-8").read()

# Ensure imports
need = [
    "from pydantic import BaseModel",
    "from fastapi import APIRouter, HTTPException, Request, Header",
]
for imp in need:
    if imp not in src:
        src = src.replace("from fastapi import APIRouter, HTTPException, Request, Header", imp+"\nfrom fastapi import APIRouter, HTTPException, Request, Header") if "from fastapi import APIRouter" in src else imp+"\n"+src

# Ensure models for reset
if "class ResetRequestIn(BaseModel)" not in src:
    models = """
class ResetRequestIn(BaseModel):
    email: str

class ResetConfirmIn(BaseModel):
    token: str
    new_password: str
"""
    insert_after = "class LogoutIn(BaseModel):"
    i = src.find(insert_after)
    if i != -1:
        j = src.find("\n", i) + 1
        src = src[:j] + models + src[j:]
    else:
        # fallback: append near other models
        src += "\n"+models

# Where to store reset tokens
if "RESET = os.path.join(AUTH_DIR, \"reset.json\")" not in src:
    src = src.replace(
        "REFRESH = os.path.join(AUTH_DIR, \"refresh.json\")",
        "REFRESH = os.path.join(AUTH_DIR, \"refresh.json\")\nRESET = os.path.join(AUTH_DIR, \"reset.json\")"
    )

# Helpers for reset store and revoke
helpers_block = """
def _load_reset():
    p = RESET
    if not os.path.exists(p): return {}
    with open(p,"r",encoding="utf-8") as f: return json.load(f)

def _save_reset(d):
    os.makedirs(AUTH_DIR, exist_ok=True)
    with open(RESET,"w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)

def _mk_reset_token(email:str):
    raw = f"{email}|{_now()}".encode()
    sig = hmac.new(JWT_SECRET.encode(), raw, hashlib.sha256).digest()
    return _b64(raw) + "." + _b64(sig)

def _check_reset_token(tok:str):
    try:
        body_b64, sig_b64 = tok.split(".")
        raw = base64.urlsafe_b64decode(body_b64 + "==")
        email, ts = raw.decode().split("|",1)
        exp_ok = (_now() - int(ts)) < 3600  # 1 hour validity
        good = _b64(hmac.new(JWT_SECRET.encode(), raw, hashlib.sha256).digest()) == sig_b64
        if not good or not exp_ok: return None
        return email
    except Exception:
        return None

def _revoke_all_refresh_for(email:str):
    store = _load_refresh()
    changed = False
    for tid, rec in store.items():
        if rec.get("user")==email and not rec.get("revoked"):
            rec["revoked"] = True
            store[tid] = rec
            changed = True
    if changed: _save_refresh(store)
"""

if "_mk_reset_token" not in src:
    # insert helpers before endpoints (after refresh/logout definitions)
    anchor = "class LogoutIn(BaseModel):"
    pos = src.find(anchor)
    pos = src.find("\n", pos) + 1 if pos!=-1 else len(src)
    src = src[:pos] + helpers_block + src[pos:]

# Add endpoints (idempotent)
if "@router.post(\"/auth/request_reset\")" not in src:
    src += """
@router.post("/auth/request_reset")
def request_reset(body: ResetRequestIn):
    users = _load_users()
    email = body.email.strip().lower()
    # Do not leak existence: always 200
    if email in users:
        token = _mk_reset_token(email)
        store = _load_reset()
        store[token] = {"email": email, "exp": _now()+3600}
        _save_reset(store)
        # In production you would email this token. For dev we return it so you can paste it in the portal.
        return {"ok": True, "dev_token": token}
    return {"ok": True}

@router.post("/auth/reset_password")
def reset_password(body: ResetConfirmIn):
    email = _check_reset_token(body.token)
    if not email: raise HTTPException(400, "bad/expired token")
    _validate_password(body.new_password)
    users = _load_users()
    if email not in users: raise HTTPException(404, "not found")
    salt = _new_salt()
    users[email]["pwd_hash"] = _pbkdf2(body.new_password, salt)
    users[email]["salt"] = _b64(salt)
    users[email]["last_pw_change"] = _now()
    _save_users(users)
    # revoke all refresh tokens for this user
    _revoke_all_refresh_for(email)
    # burn the reset token
    store = _load_reset()
    if body.token in store: 
        store[body.token]["exp"] = 0
        _save_reset(store)
    return {"ok": True}
"""

open(AUTHX, "w", encoding="utf-8").write(src)
print("AuthX patched: JSON bodies ensured earlier; added /auth/request_reset and /auth/reset_password with refresh revoke.")
