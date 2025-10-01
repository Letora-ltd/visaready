import os, re, textwrap, datetime

BACKEND = os.path.join("backend")
VALIDATE = os.path.join(BACKEND, "admin_validate.py")
ADMIN = os.path.join("frontend","admin","index.html")

today = datetime.date.today().isoformat()

# ---------- Patch backend/admin_validate.py with rich dryfix ----------
src = open(VALIDATE, "r", encoding="utf-8").read()

# Ensure imports include save_json and verify_token (idempotent)
if "from .utils import load_json, save_json, verify_token" not in src:
    src = re.sub(
        r"from \.utils import load_json(?:,\s*verify_token)?",
        "from .utils import load_json, save_json, verify_token",
        src
    )

# Replace/insert the rich dryfix function
pattern = r"@router\.post\(\"/admin/validate/dryfix\"\)[\s\S]*?def admin_validate_dryfix[\s\S]*?\n\s*return\s+\{[\s\S]*?\}\n"
block = textwrap.dedent(f"""
@router.post("/admin/validate/dryfix")
def admin_validate_dryfix(authorization: str | None = Header(default=None)):
    _auth(authorization)
    data = load_json("checklists.json")
    changes = []
    fixed_count = 0
    normalized = 0

    def is_http(u: str) -> bool:
        return isinstance(u, str) and u.lower().startswith(("http://","https://"))

    def diff(key, path, old, new):
        if (old or "") != (new or ""):
            changes.append({{"key": key, "path": path, "old": old, "new": new}})
            return True
        return False

    for key, v in list(data.items()):
        if not isinstance(v, dict):
            continue

        # last_verified
        if not (v.get("last_verified") or "").strip():
            diff(key, "last_verified", v.get("last_verified"), "{today}")
            fixed_count += 1

        # trim fees/processing
        for fld in ("fees", "processing"):
            old = v.get(fld)
            new = (old or "").strip()
            if diff(key, fld, old, new):
                normalized += 1

        # items cleanup
        items = v.get("items") or []
        new_len = 0
        for i, it in enumerate(items):
            it = it or {{}}
            title_old, details_old, src_old = it.get("title"), it.get("details"), it.get("source_url")
            title, details, srcu = (title_old or "").strip(), (details_old or "").strip(), (src_old or "").strip()

            # drop totally empty
            if not title and not details and not srcu:
                changes.append({{"key": key, "path": f"items[{i}]", "old": it, "new": None}})
                fixed_count += 1
                continue
            new_len += 1

            # normalise item URL: drop if not http(s)
            if srcu and not is_http(srcu):
                changes.append({{"key": key, "path": f"items[{i}].source_url", "old": src_old, "new": ""}})
                fixed_count += 1

            if diff(key, f"items[{i}].title", title_old, title): normalized += 1
            if diff(key, f"items[{i}].details", details_old, details): normalized += 1

        if new_len != len(items):
            changes.append({{"key": key, "path": "items.length", "old": len(items), "new": new_len}})

        # sources cleanup
        srcs = v.get("sources") or []
        for i, s in enumerate(srcs):
            s = s or {{}}
            label_old, url_old = s.get("label"), s.get("url")
            label, url = (label_old or "").strip(), (url_old or "").strip()
            if url and not is_http(url):
                changes.append({{"key": key, "path": f"sources[{i}].url", "old": url_old, "new": ""}})
                fixed_count += 1
            if diff(key, f"sources[{i}].label", label_old, label): normalized += 1
            if diff(key, f"sources[{i}].url", url_old, url): normalized += 1

    return {{"ok": True, "fixed": fixed_count, "normalized": normalized, "changes": changes}}
""").lstrip()

if re.search(pattern, src, flags=re.MULTILINE):
    src = re.sub(pattern, block, src, flags=re.MULTILINE)
else:
    # append if missing
    src += "\n\n" + block + "\n"

open(VALIDATE, "w", encoding="utf-8").write(src)

# ---------- Patch frontend/admin/index.html to retry on 401 for Dry-run/Dry-run+Apply ----------
html = open(ADMIN, "r", encoding="utf-8").read()

def inject_retry(handler_id, call_template):
    """
    Ensure the given handler retries once on 401 by forcing re-login and refetch.
    call_template is the fetch(...) string to execute after login (JS code).
    """
    global html
    # Ensure BACKEND const exists
    if "const BACKEND" not in html:
        html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

    # Find handler
    m = re.search(rf"document\.getElementById\('{re.escape(handler_id)}'\)\.onclick\s*=\s*async\s*\(\)\s*=>\s*\{{([\s\S]*?)\n\}};", html)
    if not m:
        return
    body = m.group(1)
    # If already has retry, skip
    if "/*__retry__*/" in body:
        return
    # Insert retry wrapper around the fetch for the given call
    # We add a small helper: if 401, re-login and redo once
    retry_stub = textwrap.dedent(f"""
        /*__retry__*/ 
        async function __do_call__(){{
          return {call_template};
        }}
        let __resp__ = await __do_call__();
        if (__resp__ && __resp__.status === 401) {{
          // re-login once
          if (typeof val_login === 'function') {{
            await val_login();
          }} else {{
            const pwd = (document.getElementById('val_pwd')||{{}}).value||'';
            const rL = await fetch(`${{BACKEND}}/admin/login`, {{
              method:'POST', headers:{{'Content-Type':'application/json'}},
              body: JSON.stringify({{ password: pwd.trim() }})
            }});
            if (!rL.ok) throw new Error('Re-login failed');
            window.VAL_TOKEN = (await rL.json()).token;
          }}
          __resp__ = await __do_call__();
        }}
    """).strip("\n")

    # Simple insertion: at the first occurrence of the call, we replace it with the retry stub + the rest uses __resp__
    # For dry-run button (val_dry_btn)
    if handler_id == "val_dry_btn":
        body2 = re.sub(
            r"const\s+res\s*=\s*await\s*fetch\([^\)]*\);\s*if\s*\(!res\.ok\)\s*\{",
            retry_stub + "\n        const res = __resp__;\n        if (!res.ok) {",
            body,
            count=1,
            flags=re.MULTILINE
        )
    else:
        # For dry-run+apply: first call is to /dryfix; replace that one
        body2 = re.sub(
            r"const\s+r1\s*=\s*await\s*fetch\([^\)]*\);\s*if\s*\(!r1\.ok\)\s*\{",
            retry_stub.replace("__do_call__", "__do_call__DRY").replace("return ", "return ")\
            .replace("__resp__", "__respDRY__") + "\n      const r1 = __respDRY__;\n      if (!r1.ok) {",
            body,
            count=1,
            flags=re.MULTILINE
        )
    html = html.replace(body, body2)

# Hook for Dry-run Fix button
inject_retry(
    "val_dry_btn",
    "fetch(`${BACKEND}/admin/validate/dryfix`, { method:'POST', headers:{ 'Authorization':'Bearer '+window.VAL_TOKEN } })"
)

# Hook for Dry-run + Apply button (first call to dryfix)
inject_retry(
    "val_dry_apply_btn",
    "fetch(`${BACKEND}/admin/validate/dryfix`, { method:'POST', headers:{ 'Authorization':'Bearer '+window.VAL_TOKEN } })"
)

open(ADMIN, "w", encoding="utf-8").write(html)

print("Patched: rich dry-run backend + front-end retry on 401.")
