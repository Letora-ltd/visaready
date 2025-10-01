import os, textwrap, datetime

BACKEND = os.path.join("backend")
VALIDATE = os.path.join(BACKEND, "admin_validate.py")
ADMIN_HTML = os.path.join("frontend","admin","index.html")

today = datetime.date.today().isoformat()

# ---- 1) Backend: add /admin/validate/dryfix ----
src = open(VALIDATE, "r", encoding="utf-8").read()

if "def admin_validate_dryfix" not in src:
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

    for key, v in data.items():
        if not isinstance(v, dict): continue
        v2 = dict(v)

        if not v2.get("last_verified"):
            diff(key, "last_verified", v.get("last_verified"), "{today}")
            fixed_count += 1

        for fld in ("fees","processing"):
            old = v.get(fld)
            new = (old or "").strip()
            if diff(key, fld, old, new):
                normalized += 1

        for i, it in enumerate(v.get("items") or []):
            if not it: continue
            title_old, details_old, src_old = it.get("title"), it.get("details"), it.get("source_url")
            title, details, srcu = (title_old or "").strip(), (details_old or "").strip(), (src_old or "").strip()
            if not title and not details and not srcu:
                changes.append({{"key":key,"path":f"items[{i}]","old":it,"new":None}})
                fixed_count += 1
                continue
            if srcu and not is_http(srcu):
                changes.append({{"key":key,"path":f"items[{i}].source_url","old":src_old,"new":""}})
                fixed_count += 1
            if diff(key,f"items[{i}].title",title_old,title): normalized+=1
            if diff(key,f"items[{i}].details",details_old,details): normalized+=1

        for i, s in enumerate(v.get("sources") or []):
            if not s: continue
            label_old, url_old = s.get("label"), s.get("url")
            label, url = (label_old or "").strip(), (url_old or "").strip()
            if url and not is_http(url):
                changes.append({{"key":key,"path":f"sources[{i}].url","old":url_old,"new":""}})
                fixed_count += 1
            if diff(key,f"sources[{i}].label",label_old,label): normalized+=1
            if diff(key,f"sources[{i}].url",url_old,url): normalized+=1

    return {{"ok":True,"fixed":fixed_count,"normalized":normalized,"changes":changes}}
""").lstrip()
    with open(VALIDATE,"a",encoding="utf-8") as f:
        f.write("\n"+block)

# ---- 2) Frontend: add Dry-run button & handler ----
html = open(ADMIN_HTML,"r",encoding="utf-8").read()

if 'id="val_dry_btn"' not in html:
    html = html.replace(
        'id="val_fix_btn"',
        'id="val_fix_btn" style="margin-left:8px;">Fix trivial issues</button>\n    <button class="btn" id="val_dry_btn" style="margin-left:8px;">Dry-run Fix</button'
    )

if "document.getElementById('val_dry_btn')" not in html:
    js = """
<script>
function downloadTextFile(filename, text){
  const blob=new Blob([text],{type:'text/plain;charset=utf-8;'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=filename;a.click();
  URL.revokeObjectURL(url);
}
document.getElementById('val_dry_btn').onclick=async()=>{
  const msg=document.getElementById('val_msg');
  const out=document.getElementById('val_out');
  msg.textContent='';out.textContent='';
  try{
    if(!window.VAL_TOKEN && typeof val_login==='function'){await val_login();}
    const res=await fetch(`${BACKEND}/admin/validate/dryfix`,{method:'POST',headers:{'Authorization':'Bearer '+window.VAL_TOKEN}});
    if(!res.ok){msg.textContent='Dry-run failed: '+(await res.text());return;}
    const data=await res.json();
    msg.textContent=`Dry-run — Fixed: ${data.fixed}, Normalized: ${data.normalized}, Changes: ${data.changes.length}`;
    if(!Array.isArray(data.changes)||!data.changes.length){out.textContent='No changes needed.';return;}
    out.textContent=data.changes.map(c=>`• ${c.key} — ${c.path}: ${JSON.stringify(c.old)} → ${JSON.stringify(c.new)}`).join('\\n');
    if(!document.getElementById('val_dry_dl')){
      const dl=document.createElement('button');dl.id='val_dry_dl';dl.className='btn';dl.style.marginLeft='8px';dl.textContent='Download diff';
      dl.onclick=()=>downloadTextFile('visaready_dryfix_diff.txt',out.textContent);
      document.getElementById('val_btn').parentNode.appendChild(dl);
    }
  }catch(e){console.error(e);msg.textContent='Dry-run failed';}
};
</script>
"""
    html = html.replace("</body>", js+"\n</body>")

open(ADMIN_HTML,"w",encoding="utf-8").write(html)

print("v4.4 Dry-run Fix added successfully.")
