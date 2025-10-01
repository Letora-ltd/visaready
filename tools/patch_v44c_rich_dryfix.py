import os, re, textwrap, datetime

VALIDATE = os.path.join("backend","admin_validate.py")
APP = os.path.join("backend","app.py")

today = datetime.date.today().isoformat()

# --- 1. Replace stub /admin/validate/dryfix with rich version ---
src = open(VALIDATE,"r",encoding="utf-8").read()

rich_block = textwrap.dedent(f"""
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
        if not isinstance(v, dict): continue

        # last_verified
        if not (v.get("last_verified") or "").strip():
            diff(key,"last_verified",v.get("last_verified"),"{today}")
            fixed_count += 1

        # fees / processing trims
        for fld in ("fees","processing"):
            old = v.get(fld); new = (old or "").strip()
            if diff(key,fld,old,new): normalized+=1

        # items
        items = v.get("items") or []
        new_len = 0
        for i,it in enumerate(items):
            it = it or {{}}
            t_old,d_old,s_old = it.get("title"),it.get("details"),it.get("source_url")
            t,d,s = (t_old or "").strip(),(d_old or "").strip(),(s_old or "").strip()
            if not t and not d and not s:
                changes.append({{"key":key,"path":f"items[{i}]","old":it,"new":None}})
                fixed_count+=1; continue
            new_len+=1
            if s and not is_http(s):
                changes.append({{"key":key,"path":f"items[{i}].source_url","old":s_old,"new":""}})
                fixed_count+=1
            if diff(key,f"items[{i}].title",t_old,t): normalized+=1
            if diff(key,f"items[{i}].details",d_old,d): normalized+=1
        if new_len!=len(items):
            changes.append({{"key":key,"path":"items.length","old":len(items),"new":new_len}})

        # sources
        for i,s in enumerate(v.get("sources") or []):
            if not s: continue
            l_old,u_old = s.get("label"),s.get("url")
            l,u = (l_old or "").strip(),(u_old or "").strip()
            if u and not is_http(u):
                changes.append({{"key":key,"path":f"sources[{i}].url","old":u_old,"new":""}})
                fixed_count+=1
            if diff(key,f"sources[{i}].label",l_old,l): normalized+=1
            if diff(key,f"sources[{i}].url",u_old,u): normalized+=1

    return {{"ok":True,"fixed":fixed_count,"normalized":normalized,"changes":changes}}
""")

# replace any old dryfix
src = re.sub(r"@router\.post\(\"/admin/validate/dryfix\"[\s\S]+?(?=\n@|$)", "", src, flags=re.MULTILINE)
src += "\n\n" + rich_block + "\n"
open(VALIDATE,"w",encoding="utf-8").write(src)

# --- 2. Ensure app includes admin_validate router ---
app = open(APP,"r",encoding="utf-8").read()
if "include_router(admin_validate.router)" not in app:
    if "from . import admin_validate" not in app and "import admin_validate" not in app:
        app += "\ntry:\n    from . import admin_validate\nexcept Exception:\n    import admin_validate\n"
    app += "app.include_router(admin_validate.router)\n"
    open(APP,"w",encoding="utf-8").write(app)

print("Rich /admin/validate/dryfix endpoint patched in and router ensured.")
