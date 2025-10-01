import os, re, textwrap, datetime, json

BACKEND = os.path.join("backend")
APP = os.path.join(BACKEND, "app.py")
VALIDATE = os.path.join(BACKEND, "admin_validate.py")
ADMIN_HTML = os.path.join("frontend","admin","index.html")

today = datetime.date.today().isoformat()

# ---- 1) Patch backend/admin_validate.py with /admin/validate/fix ----
src = open(VALIDATE, "r", encoding="utf-8").read()

if "def admin_validate_fix" not in src:
    fix_block = textwrap.dedent(f"""
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
            v["last_verified"] = "{today}"
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
            it = it or {{}}
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

            new_it = {{"title": title, "details": details}}
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
            s = s or {{}}
            label = (s.get("label") or "").strip()
            url = (s.get("url") or "").strip()
            if url and not is_http(url):
                # drop bad url; keep label if present
                url = ""
                fixed_count += 1
            # keep row if something remains
            if label or url:
                new_srcs.append({{"label": label, "url": url}} if url else {{"label": label}})
        v["sources"] = new_srcs

        data[key] = v

    save_json("checklists.json", data)
    return {{"ok": True, "fixed": fixed_count, "normalized": normalized}}
""").lstrip()

    # inject at end of file
    with open(VALIDATE, "a", encoding="utf-8") as f:
        f.write("\n" + fix_block)

# ---- 2) Ensure router is included in backend/app.py (already done in v4.2; keep idempotent) ----
app_src = open(APP, "r", encoding="utf-8").read()
if "include_router(admin_validate.router)" not in app_src:
    if "from . import admin_validate" not in app_src:
        app_src += "\ntry:\n    from . import admin_validate\nexcept Exception:\n    import admin_validate\n"
    app_src += "app.include_router(admin_validate.router)\n"
    open(APP, "w", encoding="utf-8").write(app_src)

# ---- 3) Add button & JS in Admin page ----
html = open(ADMIN_HTML, "r", encoding="utf-8").read()

# add button next to "Run Validation"
if 'id="val_fix_btn"' not in html:
    html = html.replace(
        'id="val_btn">Run Validation</button>',
        'id="val_btn">Run Validation</button>\n    <button class="btn" id="val_fix_btn" style="margin-left:8px;">Fix trivial issues</button>'
    )

# add handler
if "document.getElementById('val_fix_btn')" not in html:
    js = """
<script>
document.getElementById('val_fix_btn').onclick = async () => {
  const msg=document.getElementById('val_msg'); const out=document.getElementById('val_out');
  msg.textContent=''; out.textContent='';
  try{
    if(!VAL_TOKEN) await val_login();
    const res = await fetch(`${BACKEND}/admin/validate/fix`, { method:'POST', headers:{'Authorization':'Bearer '+VAL_TOKEN} });
    if(!res.ok){ msg.textContent='Fix failed: '+(await res.text()); return; }
    const data = await res.json();
    msg.textContent = `Fixed: ${data.fixed}, Normalized: ${data.normalized}. Run validation again.`;
  }catch(e){ console.error(e); msg.textContent='Fix failed'; }
};
</script>
"""
    html = html.replace("</body>", js + "\n</body>")

open(ADMIN_HTML, "w", encoding="utf-8").write(html)

print("v4.3 validate/fix added (backend) + Admin button wired.")
