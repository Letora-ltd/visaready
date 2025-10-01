import os, re, textwrap

BACKEND = os.path.join("backend")
FRONTEND = os.path.join("frontend")
ADMIN_CSV = os.path.join(FRONTEND, "admin", "csv.html")
ADMIN_INDEX = os.path.join(FRONTEND, "admin", "index.html")
ADMIN_CSV_PY = os.path.join(BACKEND, "admin_csv.py")

# ---------- 1) Replace backend/admin_csv.py with friendly import/export ----------
admin_csv_code = textwrap.dedent("""
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Response, Query
import csv, io, json, time

from .utils import load_json, save_json, verify_token

router = APIRouter()

def _auth(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Token expired/invalid")

# -------- helpers to convert friendly text <-> json arrays --------
def items_from_text(txt: str):
    """
    Parse multiline 'Title :: Details' into [{"title":..., "details":...}, ...]
    """
    items = []
    for raw in (txt or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "::" in line:
            title, details = line.split("::", 1)
        elif "-" in line:
            title, details = line.split("-", 1)
        else:
            title, details = line, ""
        items.append({"title": title.strip(), "details": details.strip()})
    return items

def items_to_text(items):
    lines = []
    for it in (items or []):
        title = (it or {}).get("title","").strip()
        details = (it or {}).get("details","").strip()
        if title or details:
            lines.append(f"{title} :: {details}".strip())
    return "\\n".join(lines)

def sources_from_text(txt: str):
    """
    Parse multiline 'Label :: URL' into [{"label":..., "url":...}, ...]
    """
    sources = []
    for raw in (txt or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "::" in line:
            label, url = line.split("::", 1)
        elif "|" in line:
            label, url = line.split("|", 1)
        else:
            # if only URL, label = URL
            label, url = line, line
        sources.append({"label": label.strip(), "url": url.strip()})
    return sources

def sources_to_text(sources):
    lines = []
    for s in (sources or []):
        label = (s or {}).get("label","").strip()
        url = (s or {}).get("url","").strip()
        if label or url:
            lines.append(f"{label} :: {url}".strip())
    return "\\n".join(lines)

@router.get("/admin/export/csv")
def admin_export_csv(
    authorization: str | None = Header(default=None),
    friendly: bool = Query(default=False, description="If true, export human-friendly columns")
):
    _auth(authorization)
    data = load_json("checklists.json")
    if friendly:
        cols = ["key","last_verified","fees","processing","items_text","sources_text"]
    else:
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
        }
        if friendly:
            row["items_text"]   = items_to_text(val.get("items",[]))
            row["sources_text"] = sources_to_text(val.get("sources",[]))
        else:
            row["items_json"]   = json.dumps(val.get("items",[]), ensure_ascii=False)
            row["sources_json"] = json.dumps(val.get("sources",[]), ensure_ascii=False)
        w.writerow(row)
    csv_bytes = buf.getvalue().encode("utf-8-sig")
    headers = {"Content-Disposition": f'attachment; filename="visaready_checklists_{int(time.time())}.csv"'}
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)

@router.post("/admin/import/csv")
async def admin_import_csv(
    authorization: str | None = Header(default=None),
    file: UploadFile = File(...),
    mode: str = "merge"
):
    """
    mode: 'merge' (update/insert) or 'replace' (overwrite everything with provided rows)
    Accepts either JSON columns (items_json, sources_json) or friendly columns (items_text, sources_text)
    """
    _auth(authorization)
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")

    body = (await file.read()).decode("utf-8-sig", errors="replace")
    r = csv.DictReader(io.StringIO(body))
    fieldset = { (c or "").strip().lower() for c in (r.fieldnames or []) }

    current = load_json("checklists.json")
    new_data = {} if mode == "replace" else dict(current)

    n = 0
    for row in r:
        key = (row.get("key") or "").strip()
        if not key: 
            continue

        # choose source format
        items = []
        sources = []
        if "items_json" in fieldset:
            try:
                items = json.loads(row.get("items_json") or "[]")
            except json.JSONDecodeError:
                raise HTTPException(400, f"Invalid items_json for key={key}")
        elif "items_text" in fieldset:
            items = items_from_text(row.get("items_text") or "")

        if "sources_json" in fieldset:
            try:
                sources = json.loads(row.get("sources_json") or "[]")
            except json.JSONDecodeError:
                raise HTTPException(400, f"Invalid sources_json for key={key}")
        elif "sources_text" in fieldset:
            sources = sources_from_text(row.get("sources_text") or "")

        entry = {
            "last_verified": (row.get("last_verified") or "").strip() or time.strftime("%Y-%m-%d"),
            "fees": (row.get("fees") or "").strip(),
            "processing": (row.get("processing") or "").strip(),
            "items": items,
            "sources": sources
        }
        new_data[key] = entry
        n += 1

    save_json("checklists.json", new_data)
    return {"ok": True, "updated": n, "mode": mode}
""").lstrip()

os.makedirs(BACKEND, exist_ok=True)
with open(ADMIN_CSV_PY, "w", encoding="utf-8") as f:
    f.write(admin_csv_code)

# ---------- 2) Patch frontend/admin/csv.html: add Friendly toggle & use ?friendly=1 ----------
if os.path.exists(ADMIN_CSV):
    html = open(ADMIN_CSV, "r", encoding="utf-8").read()

    # ensure BACKEND const exists
    if "const BACKEND" not in html:
        html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

    # add friendly checkbox near Export button (simple injection)
    if "id=\"friendly\"" not in html:
        html = html.replace(
            "id=\"exportBtn\">Export CSV</button>",
            "id=\"exportBtn\">Export CSV</button>\n      <label style=\"display:inline-flex;align-items:center;gap:6px;\">\n        <input type=\"checkbox\" id=\"friendly\"/> Friendly CSV\n      </label>"
        )

    # rewrite export handler to include ?friendly=1
    html = re.sub(
        r"fetch\(`\$\{BACKEND\}/admin/export/csv`\s*,\s*\{([^}]*)\}\)",
        "fetch(`${BACKEND}/admin/export/csv?friendly=${document.getElementById('friendly')&&document.getElementById('friendly').checked?1:0}`, {\\1})",
        html
    )

    # extend help text
    html = html.replace(
        "Columns: <code>key,last_verified,fees,processing,items_json,sources_json</code>",
        "Columns: <code>key,last_verified,fees,processing,items_json,sources_json</code> or <code>key,last_verified,fees,processing,items_text,sources_text</code>"
    ).replace(
        "items_json</em> example:",
        "items_json</em> example:"
    ) + "\n"

    with open(ADMIN_CSV, "w", encoding="utf-8") as f:
        f.write(html)

# add a quick link from index.html if missing
if os.path.exists(ADMIN_INDEX):
    idx = open(ADMIN_INDEX, "r", encoding="utf-8").read()
    if 'href="./csv.html"' not in idx:
        idx = idx.replace("</h2>", '</h2><p><a href="./csv.html">CSV Import/Export</a></p>', 1)
        with open(ADMIN_INDEX, "w", encoding="utf-8") as f:
            f.write(idx)

print("v3.5 CSV-friendly import/export applied.")
