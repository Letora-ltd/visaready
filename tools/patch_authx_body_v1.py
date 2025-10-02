import os, re, sys, textwrap

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUTHX = os.path.join(ROOT, "backend", "authx.py")

if not os.path.exists(AUTHX):
    print("ERROR: backend/authx.py not found")
    sys.exit(1)

src = open(AUTHX, "r", encoding="utf-8").read()

# Ensure BaseModel import
if "from pydantic import BaseModel" not in src:
    src = src.replace("from typing import Dict, Any", "from typing import Dict, Any\nfrom pydantic import BaseModel")

# Define input models once
if "class SetupIn(BaseModel)" not in src:
    models_block = """
class SetupIn(BaseModel):
    seed_email: str
    seed_token: str

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
    refresh: str

class LogoutIn(BaseModel):
    refresh: str
"""
    # Insert models after imports
    insert_pos = src.find("from pydantic import BaseModel")
    insert_pos = src.find("\n", insert_pos) + 1
    src = src[:insert_pos] + models_block + src[insert_pos:]

# Replace endpoint signatures to use JSON bodies (idempotent replacements)
def repl(pattern, replacement):
    global src
    if re.search(pattern, src, flags=re.MULTILINE):
        src = re.sub(pattern, replacement, src, flags=re.MULTILINE)

# /auth/setup
repl(r"@router\.post\(\"/auth/setup\"\)\s*def setup\([^\)]*\):",
     "@router.post(\"/auth/setup\")\ndef setup(body: SetupIn):")
src = src.replace("seed_email", "body.seed_email").replace("seed_token", "body.seed_token")

# /auth/signup
repl(r"@router\.post\(\"/auth/signup\"\)\s*def signup\([^\)]*\):",
     "@router.post(\"/auth/signup\")\ndef signup(body: SignupIn):")
src = src.replace("email: str, password: str", "")
src = src.replace("(email, password", "(body.email, body.password")

# /auth/signup_master
repl(r"@router\.post\(\"/auth/signup_master\"\)\s*def signup_master\([^\)]*\):",
     "@router.post(\"/auth/signup_master\")\ndef signup_master(body: SignupMasterIn):")
src = src.replace("email: str, password: str", "")
src = src.replace("(email: str", "(body: SignupMasterIn")
src = src.replace("(email,", "(body.email,").replace("password)", "body.password)")

# /auth/login
repl(r"@router\.post\(\"/auth/login\"\)\s*def login\([^\)]*\):",
     "@router.post(\"/auth/login\")\ndef login(request: Request, body: LoginIn):")
src = src.replace("email: str, password: str", "")
src = src.replace("users = _load_users()", "users = _load_users()")
src = src.replace("u = users.get(email)", "u = users.get(body.email)")
src = src.replace("_pbkdf2(password, salt) != u[\"pwd_hash\"]", "_pbkdf2(body.password, salt) != u[\"pwd_hash\"]")
src = src.replace("_mk_access(email, u.get(\"role\",\"user\"), scope)", "_mk_access(body.email, u.get(\"role\",\"user\"), scope)")
src = src.replace("_mk_refresh(email, _ua_ip_hash(request))", "_mk_refresh(body.email, _ua_ip_hash(request))")

# /auth/refresh
repl(r"@router\.post\(\"/auth/refresh\"\)\s*def refresh\([^\)]*\):",
     "@router.post(\"/auth/refresh\")\ndef refresh(request: Request, body: RefreshIn):")
src = src.replace("refresh: str", "")
src = src.replace("store = _load_refresh()", "store = _load_refresh()")
src = src.replace("rec = store.get(refresh)", "rec = store.get(body.refresh)")
src = src.replace("store[refresh] = rec", "store[body.refresh] = rec")

# /auth/logout
repl(r"@router\.post\(\"/auth/logout\"\)\s*def logout\([^\)]*\):",
     "@router.post(\"/auth/logout\")\ndef logout(body: LogoutIn):")
src = src.replace("refresh: str", "")
src = src.replace("if refresh in store:", "if body.refresh in store:")
src = src.replace("store[refresh][\"revoked\"] = True", "store[body.refresh][\"revoked\"] = True")

open(AUTHX, "w", encoding="utf-8").write(src)
print("Patched authx.py to accept JSON bodies for auth endpoints.")
