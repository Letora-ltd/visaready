import os
import time
from datetime import date, timedelta
from random import Random

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from .utils import load_json, save_json, add_token, ADMIN_PASSWORD, verify_token
except Exception:
    from utils import load_json, save_json, add_token, ADMIN_PASSWORD, verify_token

try:
    from . import user_store
except Exception:
    import user_store

app = FastAPI(title="Vixa API", version="1.0.0")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/seed")
def get_seed():
    return {
        "countries": load_json("countries.json"),
        "corridors": load_json("corridors.json"),
        "checklists": load_json("checklists.json"),
    }


@app.get("/api/corridors")
def get_countries(origin: str | None = None):
    items = load_json("corridors.json")
    if origin:
        items = [c for c in items if c.get("origin", "").upper() == origin.upper()]
    return items


@app.get("/api/visas/search")
def visa_search(origin: str, q: str = ""):
    corridors = [c for c in load_json("corridors.json") if c.get("origin", "").upper() == origin.upper()]
    if q:
        ql = q.lower()
        corridors = [
            c for c in corridors if ql in c.get("dest", "").lower() or ql in c.get("destination_name", "").lower()
        ]
    return corridors


@app.get("/api/visas/{origin}/{dest}")
def visa_detail(origin: str, dest: str):
    key = f"{origin.upper()}->{dest.upper()}::TOURIST"
    checklists = load_json("checklists.json")
    corridor = next(
        (c for c in load_json("corridors.json") if c.get("origin", "").upper() == origin.upper() and c.get("dest", "").upper() == dest.upper()),
        None,
    )
    if not corridor:
        raise HTTPException(404, "Corridor not found")
    return {"corridor": corridor, "checklist": checklists.get(key, {"items": []})}


@app.get("/api/slots/realtime")
def realtime_slots(origin: str, dest: str):
    seed = f"{origin.upper()}-{dest.upper()}-{date.today().isoformat()}"
    rnd = Random(seed)
    days = []
    for i in range(10):
        d = date.today() + timedelta(days=i)
        days.append(
            {
                "date": d.isoformat(),
                "availability": rnd.choice(["HIGH", "MEDIUM", "LOW"]),
                "eta_days": rnd.randint(2, 16),
                "last_updated": int(time.time()),
            }
        )
    return {"origin": origin.upper(), "dest": dest.upper(), "slots": days}


class SignupIn(BaseModel):
    name: str
    email: str
    password: str
    country_code: str


class LoginIn(BaseModel):
    email: str
    password: str


class ApplicationIn(BaseModel):
    origin: str
    destination: str
    visa_type: str = "TOURIST"
    travel_date: str = ""


class DocUploadIn(BaseModel):
    application_id: str
    name: str


class PaymentIntentIn(BaseModel):
    application_id: str


def _user(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ", 1)[1]
    user = user_store.get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user


@app.post("/auth/signup")
def signup(payload: SignupIn):
    if len(payload.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user = user_store.create_user(payload.name, payload.email, payload.password, payload.country_code)
    if not user:
        raise HTTPException(409, "User already exists")
    token = user_store.new_session(user["id"])
    return {"token": token, "user": user}


@app.post("/auth/login")
def login(payload: LoginIn):
    user = user_store.login(payload.email, payload.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    token = user_store.new_session(user["id"])
    return {"token": token, "user": user}


@app.get("/auth/me")
def me(authorization: str | None = Header(default=None)):
    return _user(authorization)


@app.post("/api/applications")
def create_application(payload: ApplicationIn, authorization: str | None = Header(default=None)):
    return user_store.add_application(_user(authorization)["id"], payload.model_dump())


@app.get("/api/applications")
def list_applications(authorization: str | None = Header(default=None)):
    return user_store.list_applications(_user(authorization)["id"])


@app.post("/api/documents/upload")
def upload_document(payload: DocUploadIn, authorization: str | None = Header(default=None)):
    res = user_store.attach_document(_user(authorization)["id"], payload.application_id, payload.name)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


@app.post("/api/payments/intent")
def create_payment(payload: PaymentIntentIn, authorization: str | None = Header(default=None)):
    res = user_store.create_payment_intent(_user(authorization)["id"], payload.application_id)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


@app.post("/api/applications/{app_id}/submit")
def submit(app_id: str, authorization: str | None = Header(default=None)):
    res = user_store.update_status(_user(authorization)["id"], app_id, "SUBMITTED")
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


class AdminLoginIn(BaseModel):
    password: str


@app.post("/admin/login")
def admin_login(payload: AdminLoginIn):
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid password")
    return {"token": add_token(24)}


def _auth(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ", 1)[1]
    if not verify_token(token):
        raise HTTPException(401, "Invalid token")


@app.get("/admin/checklists")
def admin_checklists(authorization: str | None = Header(default=None)):
    _auth(authorization)
    return load_json("checklists.json")


class PutChecklist(BaseModel):
    key: str
    data: dict


@app.put("/admin/checklists")
def admin_put(payload: PutChecklist, authorization: str | None = Header(default=None)):
    _auth(authorization)
    data = load_json("checklists.json")
    payload.data.setdefault("last_verified", time.strftime("%Y-%m-%d"))
    data[payload.key] = payload.data
    save_json("checklists.json", data)
    return {"ok": True}
