
from fastapi import HTTPException
def allow_write(route: str) -> bool:
    # whitelist write endpoints; deny by default
    return route in {
        "/admin/checklists:PUT",
        "/admin/duplicate:POST",
        "/admin/duplicate/bulk:POST",
        "/admin/validate/fix:POST",
        "/admin/import/csv:POST"
    }
def check_scope(role:str, scope:dict, key:str|None):
    if not key: return
    try:
        corr, purpose = key.split("::",1)
        origin, dest = corr.split("->",1)
    except Exception:
        raise HTTPException(400, "Bad key format")
    countries = (scope or {}).get("countries") or []
    visa_types = (scope or {}).get("visa_types") or []
    read_only = bool((scope or {}).get("read_only",False))
    if read_only: raise HTTPException(403, "Read-only role")
    if countries and (origin.upper() not in countries and dest.upper() not in countries):
        raise HTTPException(403, "Region not in scope")
    if visa_types and purpose.upper() not in visa_types:
        raise HTTPException(403, "Visa type not in scope")
