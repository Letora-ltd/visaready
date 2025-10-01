from fastapi import APIRouter, Header, HTTPException
import re
from .utils import load_json, verify_token

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
