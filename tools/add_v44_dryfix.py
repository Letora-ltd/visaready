import os, textwrap, datetime, json, re

BACKEND = os.path.join("backend")
VALIDATE = os.path.join(BACKEND, "admin_validate.py")
ADMIN_HTML = os.path.join("frontend","admin","index.html")

today = datetime.date.today().isoformat()

# ---- 1) Backend: add /admin/validate/dryfix (no write, returns proposed changes) ----
vsrc = open(VALIDATE, "r", encoding="utf-8").read()

if "def admin_validate_dryfix" not in vsrc:
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
        v2 = json.loads(json.dumps(v))  # deep copy

        # ensure fields exist
        v2.setdefault("fees", (v2.get("fees") or "").strip())
        v2.setdefault("processing", (v2.get("processing") or "").strip())
        v2.setdefault("last_verified", (v2.get("last_verified") or "").strip())

        # last_verified
        if not v2["last_verified"]:
            v2["last_verified"] = "{today}"
            fixed_count += 1
            diff(key, "last_verified", v.get("last_verified"), v2["last_verified"])

        # trim fees/processing
        for fld in ("fees", "processing"):
            old = v.get(fld)
            new = (v2.get(fld) or "").strip()
            if diff(key, fld, old, new):
                normalized += 1

        # items cleanup
        items = v.get("items") or []
        new_items = []
        for i, it in enumerate(items):
            it = it or {{}}
            title_old = it.get("title")
            details_old = it.get("details")
            src_old = it.get("source_url")

            title = (title_old or "").strip()
            details = (details_old or "").strip()
            srcu = (src_old or "").strip()

            # drop totally empty
            if not title and not details and not srcu:
                fixed_count += 1
                changes.append({{"key": key, "path": f"items[{i}]", "old": it, "new": None}})
                continue

            # normalise url: drop if not http(s)
            if srcu and not is_http(srcu):
                changes.append({{"key": key, "path": f"items[{i}].source_url", "old": src_old, "new": ""}})
                srcu = ""

            if diff(key, f"items[{i}].title", title_old, title):
                normalized += 1
            if diff(key, f"items[{i}].details", details_old, details):
                normalized += 1

            new_it = {{"title": title, "details": details}}
            if srcu:
                new_it["source_url"] = srcu
            new_items.append(new_it)
        # if item count changed
        if len(new_items) != len(items):
            changes.append({{"key": key, "path": "items.length", "old": len(items), "new": len(new_items)}})

        # sources cleanup
        srcs = v.get("sources") or []
        new_srcs = []
        for i, s in enumerate(srcs):
            s = s or {{}}
            label_old = s.get("label")
            url_old = s.get("url")
            label = (label_old or "").strip()
            url = (url_old or "").strip()
            if url and not is_http(url):
                changes.append({{"key": key, "path": f"sources[{i}].url", "old": url_old, "new": ""}})
                url = ""
            # keep if something remains
            if label or url:
                if diff(key, f"sources[{i}].label", label_old, label):
                    normalized += 1
                if diff(key, f"sources[{i}].url",   url_old,   url):
                    normalized += 1
                new_srcs.append({{"label": label, "url": url}} if url else {{"label": label}})

        # note: we don't write v2; dry-run only

    return {{"ok": True, "fixed": fixed_count, "normalized": normalized, "changes": changes}}
""").lstrip()
    with open(VALIDATE, "a", encoding="utf-8") as f:
        f.write("\n" + block)

# ---- 2) Frontend Admin: add "Dry-run Fix" button + handler ----
html = open(ADMIN_HTML, "r", encoding="utf-8").read()

# Add button if missing
if 'id="val_dry_btn"' not in html:
    html = html.replace(
        'id="val_fix_btn"',
        'id="val_fix_btn"\n    >Fix trivial issues</button>\n    <button class="btn" id="val_dry_btn" style="margin-left:8px;">Dry-run Fix</button><button class="btn" id="val_fix_btn" style="display:none"'
    )
    # The replace above is a trick to insert Dry-run next to Fix without hunting positions.
    # Immediately fix the accidental duplicate id:
    html = html.replace('id="val_fix_btn" style="display:none"', 'id="val_fix_btn_hidden" style="display:none"')

# Add download helper and handler if missing
if "function downloadTextFile(" not in html:
    html = html.replace("</body>", """
<script>
function downloadTextFile(filename, text){
  const blob = new Blob([text], {type:'text/plain;charset=utf-8;'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

document.getElementById('val_dry_btn').onclick = async () => {
  const msg=document.getElementById('val_msg');
  const out=document.getElementById('val_out');
  msg.textContent=''; out.textContent='';
  try{
    if(!window.VAL_TOKEN && typeof val_login==='function'){ await val_login(); }
    const res = await fetch(`${BACKEND}/admin/validate/dryfix`, { method:'POST', headers:{'Authorization':'Bearer '+window.VAL_TOKEN} });
    if(!res.ok){ msg.textContent='Dry-run failed: '+(await res.text()); return; }
    const data = await res.json();
    msg.textContent = `Dry-run — Fixed: ${data.fixed}, Normalized: ${data.normalized}, Changes: ${data.changes.length}`;
    if(!Array.isArray(data.changes) || data.changes.length===0){ out.textContent='No changes needed.'; return; }
    const lines = data.changes.map(c => `• ${c.key} — ${c.path}: ${JSON.stringify(c.old)} → ${JSON.stringify(c.new)}`);
    out.textContent = lines.join('\\n');

    // Add a lightweight "Download diff" inline button if not present:
    if(!document.getElementById('val_dry_dl')){
      const btn = document.createElement('button');
      btn.id='val_dry_dl'; btn.className='btn'; btn.textContent='Download diff';
      btn.style.marginLeft='8px';
      btn.onclick = ()=> downloadTextFile('visaready_dryfix_diff.txt', out.textContent);
      document.getElementById('val_btn').parentNode.appendChild(btn);
    }
  }catch(e){ console.error(e); msg.textContent='Dry-run failed'; }
};
</script>
</body>""")
# Ensure BACKEND const
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

open(ADMIN_HTML, "w", encoding="utf-8").write(html)

print("v4.4 dry-run fix added (backend endpoint + Admin button and diff download).")
