from fastapi import APIRouter, Header, HTTPException
import re
from .utils import load_json, save_json, verify_token

router = APIRouter()

def _auth(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Token expired/invalid")

URL_RE = re.compile(r'^https?://', re.I)

@router.get("/admin/validate")
def admin_validate(authorization: str | None = Header(default=None)):
    _auth(authorization)
    data = load_json("checklists.json")
    issues = []
    for key, v in data.items():
        # required structure
        if not isinstance(v, dict):
            issues.append({"key": key, "issue": "Entry is not an object"})
            continue
        items = v.get("items", [])
        if not items:
            issues.append({"key": key, "issue": "No items"})
        else:
            for i, it in enumerate(items, 1):
                t = (it or {}).get("title", "")
                if not t:
                    issues.append({"key": key, "issue": f"Item {i} missing title"})
                # optional URL on item
                srcu = (it or {}).get("source_url")
                if srcu and not URL_RE.match(srcu):
                    issues.append({"key": key, "issue": f"Item {i} source_url not http(s): {srcu}"})
        # sources format
        for s in v.get("sources", []) or []:
            u = (s or {}).get("url", "")
            if u and not URL_RE.match(u):
                issues.append({"key": key, "issue": f"Source url not http(s): {u}"})
        # fees/processing
        if "fees" not in v or not str(v.get("fees","")).strip():
            issues.append({"key": key, "issue": "Missing fees"})
        if "processing" not in v or not str(v.get("processing","")).strip():
            issues.append({"key": key, "issue": "Missing processing"})
        # last_verified
        if "last_verified" not in v or not str(v.get("last_verified","")).strip():
            issues.append({"key": key, "issue": "Missing last_verified"})
    return {"ok": True, "count": len(issues), "issues": issues}

@router.post("/admin/validate/fix")
def admin_validate_fix(authorization: str | None = Header(default=None)):
    _auth(authorization)
    data = load_json("checklists.json")
    fixed_count = 0
    normalized = 0

    def is_http(u: str) -> bool:
        return isinstance(u, str) and u.lower().startswith(("http://","https://"))

    for key, v in list(data.items()):
        if not isinstance(v, dict):
            continue

        # ensure fields exist
        v.setdefault("fees", (v.get("fees") or "").strip())
        v.setdefault("processing", (v.get("processing") or "").strip())
        v.setdefault("last_verified", (v.get("last_verified") or "").strip())

        # last_verified
        if not v["last_verified"]:
            v["last_verified"] = "2025-10-01"
            fixed_count += 1

        # trim strings
        for fld in ("fees", "processing"):
            newv = (v.get(fld) or "").strip()
            if newv != v.get(fld, ""):
                v[fld] = newv
                normalized += 1

        # items cleanup
        items = v.get("items") or []
        new_items = []
        for it in items:
            it = it or {}
            title = (it.get("title") or "").strip()
            details = (it.get("details") or "").strip()
            srcu = (it.get("source_url") or "").strip()

            # drop totally empty lines
            if not title and not details and not srcu:
                fixed_count += 1
                continue

            # normalise url: drop if not http(s)
            if srcu and not is_http(srcu):
                srcu = ""
                fixed_count += 1

            new_it = {"title": title, "details": details}
            if srcu:
                new_it["source_url"] = srcu
            # count trims
            if (title != (it.get("title") or "")) or (details != (it.get("details") or "")):
                normalized += 1

            new_items.append(new_it)
        v["items"] = new_items

        # sources cleanup
        srcs = v.get("sources") or []
        new_srcs = []
        for s in srcs:
            s = s or {}
            label = (s.get("label") or "").strip()
            url = (s.get("url") or "").strip()
            if url and not is_http(url):
                # drop bad url; keep label if present
                url = ""
                fixed_count += 1
            # keep row if something remains
            if label or url:
                new_srcs.append({"label": label, "url": url} if url else {"label": label})
        v["sources"] = new_srcs

        data[key] = v

    save_json("checklists.json", data)
    return {"ok": True, "fixed": fixed_count, "normalized": normalized}


@router.post("/admin/validate/dryfix")
def admin_validate_dryfix(authorization: str | None = Header(default=None)):
    _auth(authorization)
    data = load_json("checklists.json")
    # no-op preview; replace with your detailed diff logic if already added
    return {"ok": True, "fixed": 0, "normalized": 0, "changes": []}
