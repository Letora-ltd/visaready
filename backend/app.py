import os, time
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    from . import admin_csv
except Exception:
    import admin_csv

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
