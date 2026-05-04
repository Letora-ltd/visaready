import os, time
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from utils import load_json, save_json, add_token, ADMIN_PASSWORD, verify_token
except ImportError:
    from .utils import load_json, save_json, add_token, ADMIN_PASSWORD, verify_token

app = FastAPI(title="VisaReady API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Public API --------
@app.get("/api/seed")
def get_seed():
    return {
        "countries": load_json("countries.json"),
        "corridors": load_json("corridors.json"),
        "checklists": load_json("checklists.json"),
    }

@app.get("/api/countries")
def get_countries():
    return load_json("countries.json")

@app.get("/api/corridors")
def get_corridors(origin: str | None = None, dest: str | None = None):
    items = load_json("corridors.json")
    if origin: items = [c for c in items if c["origin"] == origin.upper()]
    if dest: items = [c for c in items if c["dest"] == dest.upper()]
    return items

@app.get("/api/checklist")
def get_checklist(origin: str, dest: str, category: str = "TOURIST"):
    key = f"{origin.upper()}->{dest.upper()}::{category.upper()}"
    data = load_json("checklists.json")
    if key not in data:
        raise HTTPException(404, "Checklist not found.")
    return data[key]


try:
    import user_store
except ImportError:
    from . import user_store

class SignupIn(BaseModel):
    name: str
    email: str
    password: str
    country_code: str

class LoginUserIn(BaseModel):
    email: str
    password: str

class ApplicationIn(BaseModel):
    origin: str
    destination: str
    visa_type: str = "TOURIST"
    travel_date: str = ""
    documents: list[str] = []

@app.post("/auth/signup")
def signup(payload: SignupIn):
    created = user_store.create_user(payload.name, payload.email, payload.password, payload.country_code)
    if not created:
        raise HTTPException(409, "User already exists")
    token = user_store.new_session(created["id"])
    return {"token": token, "user": created}

@app.post("/auth/login")
def login_user(payload: LoginUserIn):
    user = user_store.login(payload.email, payload.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token = user_store.new_session(user["id"])
    return {"token": token, "user": user}

def _user(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ",1)[1]
    user = user_store.get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user

@app.get("/auth/me")
def auth_me(authorization: str | None = Header(default=None)):
    return _user(authorization)

@app.get("/api/applications")
def get_apps(authorization: str | None = Header(default=None)):
    user = _user(authorization)
    return user_store.list_applications(user["id"])

@app.post("/api/applications")
def create_app(payload: ApplicationIn, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    return user_store.add_application(user["id"], payload.model_dump())

@app.get("/api/visas/search")
def visa_search(origin: str, q: str = ""):
    origin = origin.upper()
    corridors = [c for c in load_json("corridors.json") if c.get("origin","").upper() == origin]
    if q:
        ql = q.lower()
        corridors = [c for c in corridors if ql in c.get("destination_name", c.get("dest","")).lower() or ql in c.get("dest","").lower()]
    return corridors

@app.get("/api/slots")
def get_slots(origin: str = "GB", dest: str | None = None):
    # Mock data for Schengen visa slots
    slots = load_json("slots.json")
    if dest:
        slots = [s for s in slots if s["dest"].upper() == dest.upper()]
    return slots

@app.get("/api/visas/{origin}/{dest}")
def visa_detail(origin: str, dest: str):
    key = f"{origin.upper()}->{dest.upper()}::TOURIST"
    checklists = load_json("checklists.json")
    corridor = next((c for c in load_json("corridors.json") if c.get("origin","").upper()==origin.upper() and c.get("dest","").upper()==dest.upper()), None)
    if not corridor:
        raise HTTPException(404, "Corridor not found")
    return {"corridor": corridor, "checklist": checklists.get(key)}

class DocUploadIn(BaseModel):
    application_id: str
    name: str
    content_base64: str = ""

@app.post("/api/documents/upload")
def upload_document(payload: DocUploadIn, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    return user_store.attach_document(user["id"], payload.application_id, payload.name)

class PaymentIntentIn(BaseModel):
    application_id: str

@app.post("/api/payments/intent")
def payment_intent(payload: PaymentIntentIn, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    return user_store.create_payment_intent(user["id"], payload.application_id)

@app.post("/api/applications/{app_id}/submit")
def submit_application(app_id: str, authorization: str | None = Header(default=None)):
    user = _user(authorization)
    return user_store.update_status(user["id"], app_id, "SUBMITTED")

# -------- Admin auth helpers --------
class LoginIn(BaseModel):
    password: str

@app.post("/admin/login")
def admin_login(payload: LoginIn):
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = add_token(24)
    return {"token": token}

def _auth(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ",1)[1]
    if not verify_token(token):
        raise HTTPException(401, "Token expired/invalid")

@app.get("/admin/checklists")
def admin_list(authorization: str | None = Header(default=None)):
    _auth(authorization)
    return load_json("checklists.json")

class PutChecklist(BaseModel):
    key: str
    data: dict

@app.put("/admin/checklists")
def admin_put(payload: PutChecklist, authorization: str | None = Header(default=None)):
    _auth(authorization)
    data = load_json("checklists.json")
    if "last_verified" not in payload.data:
        payload.data["last_verified"] = time.strftime("%Y-%m-%d")
    data[payload.key] = payload.data
    save_json("checklists.json", data)
    return {"ok": True, "key": payload.key}

# -------- Include CSV router LAST (no circular) --------
try:
    import admin_csv
except ImportError:
    from . import admin_csv

# -------- Duplicate corridor --------
class DuplicateIn(BaseModel):
    src_key: str
    dst_key: str
    overwrite: bool = False
    copy_fees_processing: bool = True
    copy_sources: bool = True

@app.post("/admin/duplicate")
def admin_duplicate(payload: DuplicateIn, authorization: str | None = Header(default=None)):
    _auth(authorization)

    def split_key(k: str):
        # expects ORIGIN->DEST::PURPOSE
        if "::" not in k or "->" not in k:
            raise HTTPException(400, "Bad key format; expected ORIGIN->DEST::PURPOSE")
        corr, purpose = k.split("::", 1)
        origin, dest = corr.split("->", 1)
        return origin.upper(), dest.upper(), purpose.upper()

    # Load and validate
    data = load_json("checklists.json")
    if payload.src_key not in data:
        # try normalized case-match
        o, d, p = split_key(payload.src_key)
        norm_src = f"{o}->{d}::{p}"
        if norm_src not in data:
            raise HTTPException(404, f"Source key not found: {payload.src_key}")
        payload.src_key = norm_src

    o2, d2, p2 = split_key(payload.dst_key)
    dst_key = f"{o2}->{d2}::{p2}"

    if (not payload.overwrite) and dst_key in data:
        raise HTTPException(409, f"Destination key exists: {dst_key}. Enable overwrite to replace.")

    src_entry = data[payload.src_key]
    new_entry = {
        "items": list(src_entry.get("items", [])),
        "last_verified": src_entry.get("last_verified", ""),
    }
    if payload.copy_fees_processing:
        new_entry["fees"] = src_entry.get("fees", "")
        new_entry["processing"] = src_entry.get("processing", "")
    if payload.copy_sources:
        new_entry["sources"] = list(src_entry.get("sources", []))

    data[dst_key] = new_entry
    save_json("checklists.json", data)
    return {"ok": True, "dst_key": dst_key}


# -------- Bulk duplicate corridors --------
class BulkDuplicateIn(BaseModel):
    src_key: str
    dst_keys: list[str]
    overwrite: bool = False
    copy_fees_processing: bool = True
    copy_sources: bool = True

@app.post("/admin/duplicate/bulk")
def admin_duplicate_bulk(payload: BulkDuplicateIn, authorization: str | None = Header(default=None)):
    _auth(authorization)

    def norm_key(k: str):
        if "::" not in k or "->" not in k:
            raise HTTPException(400, f"Bad key format: {k} (expected ORIGIN->DEST::PURPOSE)")
        corr, purpose = k.split("::", 1)
        origin, dest = corr.split("->", 1)
        return f"{origin.upper()}->{dest.upper()}::{purpose.upper()}"

    data = load_json("checklists.json")
    src_key = norm_key(payload.src_key)
    if src_key not in data:
        raise HTTPException(404, f"Source key not found: {src_key}")

    src_entry = data[src_key]
    made, skipped = [], []

    for raw in payload.dst_keys:
        if not raw.strip(): continue
        dst_key = norm_key(raw.strip())
        if (not payload.overwrite) and dst_key in data:
            skipped.append(dst_key); continue

        new_entry = {
            "items": list(src_entry.get("items", [])),
            "last_verified": src_entry.get("last_verified", ""),
        }
        if payload.copy_fees_processing:
            new_entry["fees"] = src_entry.get("fees", "")
            new_entry["processing"] = src_entry.get("processing", "")
        if payload.copy_sources:
            new_entry["sources"] = list(src_entry.get("sources", []))

        data[dst_key] = new_entry
        made.append(dst_key)

    save_json("checklists.json", data)
    return {"ok": True, "created_or_updated": made, "skipped": skipped}

app.include_router(admin_csv.router)

try:
    import admin_validate
except ImportError:
    from . import admin_validate
app.include_router(admin_validate.router)


# ===== v48 RBAC & Audit (appended) =====
try:
    import admin_rbac
except ImportError:
    from . import admin_rbac
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

# ===== v49 AUTHX & RBAC2 (appended) =====
try:
    import authx
except ImportError:
    from . import authx
try:
    import rbac2
except ImportError:
    from . import rbac2

from fastapi import Request, Header
import json as _json

app.include_router(authx.router)

@app.middleware("http")
async def auth_rbac_mw(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()
    route_key = f"{path}:{method}"
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
            payload = _json.loads(body_bytes.decode() or "{}")
        except Exception:
            payload = {}
        key = payload.get("key") or payload.get("dst_key") or None
        if not claims:
            from fastapi import HTTPException
            raise HTTPException(401, "Missing/invalid access token")
        # scope checks
        rbac2.check_scope(claims.get("role",""), (claims.get("scope") or {}), key)
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request._receive = receive
    response = await call_next(request)
    return response
