
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
