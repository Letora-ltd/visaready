import os, textwrap

BACKEND = os.path.join("backend")
FRONTEND = os.path.join("frontend")
APP = os.path.join(BACKEND, "app.py")
CSV_ROUTER = os.path.join(BACKEND, "admin_csv.py")
ADMIN_INDEX = os.path.join(FRONTEND, "admin", "index.html")
ADMIN_CSV = os.path.join(FRONTEND, "admin", "csv.html")

# --- 1) Create backend/admin_csv.py ---
router_code = textwrap.dedent("""
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Response
import csv, io, json, time
from .app import _auth, load_json, save_json

router = APIRouter()

@router.get("/admin/export/csv")
def admin_export_csv(authorization: str | None = Header(default=None)):
    _auth(authorization)
    data = load_json("checklists.json")
    cols = ["key","last_verified","fees","processing","items_json","sources_json"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for key, val in data.items():
        row = {
            "key": key,
            "last_verified": val.get("last_verified",""),
            "fees": val.get("fees",""),
            "processing": val.get("processing",""),
            "items_json": json.dumps(val.get("items",[]), ensure_ascii=False),
            "sources_json": json.dumps(val.get("sources",[]), ensure_ascii=False)
        }
        w.writerow(row)
    csv_bytes = buf.getvalue().encode("utf-8-sig")
    headers = {
        "Content-Disposition": f'attachment; filename="visaready_checklists_{int(time.time())}.csv"'
    }
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)

@router.post("/admin/import/csv")
async def admin_import_csv(authorization: str | None = Header(default=None),
                           file: UploadFile = File(...),
                           mode: str = "merge"):
    _auth(authorization)
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")
    body = (await file.read()).decode("utf-8-sig", errors="replace")
    r = csv.DictReader(io.StringIO(body))
    current = load_json("checklists.json")
    new_data = {} if mode == "replace" else dict(current)
    n = 0
    for row in r:
        key = (row.get("key") or "").strip()
        if not key: continue
        try:
            items = json.loads(row.get("items_json") or "[]")
            sources = json.loads(row.get("sources_json") or "[]")
        except json.JSONDecodeError:
            raise HTTPException(400, f"Invalid JSON in items_json/sources_json for key={key}")
        entry = {
            "last_verified": row.get("last_verified") or time.strftime("%Y-%m-%d"),
            "fees": row.get("fees") or "",
            "processing": row.get("processing") or "",
            "items": items,
            "sources": sources
        }
        new_data[key] = entry
        n += 1
    save_json("checklists.json", new_data)
    return {"ok": True, "updated": n, "mode": mode}
""")

os.makedirs(BACKEND, exist_ok=True)
with open(CSV_ROUTER, "w", encoding="utf-8") as f:
    f.write(router_code)

# --- 2) Patch backend/app.py to include the new router ---
with open(APP, "r", encoding="utf-8") as f:
    app_py = f.read()
if "include_router(admin_csv.router)" not in app_py:
    if "from . import admin_csv" not in app_py:
        app_py += "\nfrom . import admin_csv\n"
    app_py += "app.include_router(admin_csv.router)\n"
    with open(APP, "w", encoding="utf-8") as f:
        f.write(app_py)

# --- 3) Add frontend/admin/csv.html ---
os.makedirs(os.path.join(FRONTEND, "admin"), exist_ok=True)
csv_html = """<!doctype html><html><head><meta charset='utf-8'><title>VisaReady CSV Admin</title>
<link rel='stylesheet' href='../style.css'></head><body class='container'>
<h1 class='h2'>CSV Export / Import</h1>
<p><a href='./index.html'>← Back to Admin</a></p>
<p>Use Export to download all checklists. Use Import to upload a CSV with columns
<code>key,last_verified,fees,processing,items_json,sources_json</code>.</p>
</body></html>"""
with open(ADMIN_CSV, "w", encoding="utf-8") as f:
    f.write(csv_html)

print("v3.4 CSV Import/Export: backend endpoints + admin UI added.")
