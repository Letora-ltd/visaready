
import os, json, time, secrets
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

APP_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "seed")

def load_json(name):
    with open(os.path.join(DATA_DIR, name),"r") as f: return json.load(f)
def save_json(name, obj):
    tmp = os.path.join(DATA_DIR, name + ".tmp")
    with open(tmp, "w") as f: json.dump(obj, f, indent=2)
    os.replace(tmp, os.path.join(DATA_DIR, name))

app = FastAPI(title="VisaReady API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/seed")
def get_seed():
    return {
        "countries": load_json("countries.json"),
        "corridors": load_json("corridors.json"),
        "checklists": load_json("checklists.json"),
    }

@app.get("/api/countries")
def get_countries(): return load_json("countries.json")

@app.get("/api/corridors")
def get_corridors(origin: str = None, dest: str = None):
    items = load_json("corridors.json")
    if origin: items = [c for c in items if c["origin"] == origin.upper()]
    if dest: items = [c for c in items if c["dest"] == dest.upper()]
    return items

@app.get("/api/checklist")
def get_checklist(origin: str, dest: str, category: str = "TOURIST"):
    key = f"{origin.upper()}->{dest.upper()}::{category.upper()}"
    data = load_json("checklists.json")
    if key not in data: raise HTTPException(404, "Checklist not found.")
    return data[key]

# ----- Admin -----
class LoginIn(BaseModel):
    password: str

@app.post("/admin/login")
def admin_login(payload: LoginIn):
    if payload.password != APP_ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid password")
    token = secrets.token_hex(16)
    # naive in-memory token store
    TOKENS[token] = time.time() + 86400  # 24h
    return {"token": token}

TOKENS = {}

def _auth(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ",1)[1]
    if token not in TOKENS or TOKENS[token] < time.time():
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
    # auto-stamp last_verified if not present
    if "last_verified" not in payload.data:
        payload.data["last_verified"] = time.strftime("%Y-%m-%d")
    data[payload.key] = payload.data
    save_json("checklists.json", data)
    return {"ok": True, "key": payload.key}

from . import admin_csv
app.include_router(admin_csv.router)
