import os, re

APP = os.path.join("backend","app.py")
ADMIN = os.path.join("frontend","admin","index.html")

# ---- Backend: add /admin/duplicate/bulk ----
with open(APP, "r", encoding="utf-8") as f:
    src = f.read()

if "/admin/duplicate/bulk" not in src:
    block = r"""
# -------- Bulk duplicate corridors --------
class BulkDuplicateIn(BaseModel):
    src_key: str
    dst_keys: list[str]
    overwrite: bool = False
    copy_fees_processing: bool = True
    copy_sources: bool = True

@app.post("/admin/duplicate/bulk")
def admin_duplicate_bulk(payload: BulkDuplicateIn, authorization: str | None = Header(default=None)):
    _auth(authorization)

    def norm_key(k: str):
        if "::" not in k or "->" not in k:
            raise HTTPException(400, f"Bad key format: {k} (expected ORIGIN->DEST::PURPOSE)")
        corr, purpose = k.split("::", 1)
        origin, dest = corr.split("->", 1)
        return f"{origin.upper()}->{dest.upper()}::{purpose.upper()}"

    data = load_json("checklists.json")
    src_key = norm_key(payload.src_key)
    if src_key not in data:
        raise HTTPException(404, f"Source key not found: {src_key}")

    src_entry = data[src_key]
    made, skipped = [], []

    for raw in payload.dst_keys:
        if not raw.strip(): continue
        dst_key = norm_key(raw.strip())
        if (not payload.overwrite) and dst_key in data:
            skipped.append(dst_key); continue

        new_entry = {
            "items": list(src_entry.get("items", [])),
            "last_verified": src_entry.get("last_verified", ""),
        }
        if payload.copy_fees_processing:
            new_entry["fees"] = src_entry.get("fees", "")
            new_entry["processing"] = src_entry.get("processing", "")
        if payload.copy_sources:
            new_entry["sources"] = list(src_entry.get("sources", []))

        data[dst_key] = new_entry
        made.append(dst_key)

    save_json("checklists.json", data)
    return {"ok": True, "created_or_updated": made, "skipped": skipped}
"""
    ins = src.rfind("app.include_router(admin_csv.router)")
    src = (src[:ins] + block + "\n" + src[ins:]) if ins != -1 else (src + "\n" + block)
    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

# ---- Admin UI card ----
with open(ADMIN, "r", encoding="utf-8") as f:
    html = f.read()

if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

if 'id="bulkDupCard"' not in html:
    card = """
<section class="card" id="bulkDupCard">
  <h2 class="h2">Bulk Duplicate</h2>
  <p class="small">Clone one key to many. One destination per line (e.g., <code>IN-&gt;FR::TOURIST</code>).</p>
  <div class="grid">
    <div><div class="label">Source key</div><input id="bdup_src" placeholder="IN->DE::TOURIST"></div>
    <div><div class="label">Admin Password</div><input id="bdup_pwd" type="password" placeholder="Enter admin password"></div>
  </div>
  <div class="grid" style="margin-top:10px;">
    <div>
      <div class="label">Destination keys (one per line)</div>
      <textarea id="bdup_dst" rows="8" placeholder="IN->ES::TOURIST&#10;IN->IT::TOURIST&#10;IN->NL::TOURIST"></textarea>
    </div>
  </div>
  <div style="margin-top:10px; display:flex; gap:12px; flex-wrap:wrap;">
    <label style="display:inline-flex;align-items:center;gap:6px;">
      <input type="checkbox" id="bdup_overwrite"> Overwrite if exists
    </label>
    <label style="display:inline-flex;align-items:center;gap:6px;">
      <input type="checkbox" id="bdup_copy_fp" checked> Copy fees & processing
    </label>
    <label style="display:inline-flex;align-items:center;gap:6px;">
      <input type="checkbox" id="bdup_copy_src" checked> Copy sources
    </label>
    <button class="btn" id="bdup_btn">Duplicate</button>
    <span id="bdup_msg" class="small"></span>
  </div>
</section>
"""
    html = html.replace("</main>", card + "\n</main>")

if "function bdup_login(" not in html:
    js = """
<script>
let BDUP_TOKEN = null;
async function bdup_login(){
  const pwd = document.getElementById('bdup_pwd').value.trim();
  if(!pwd) throw new Error("Enter admin password");
  const res = await fetch(`${BACKEND}/admin/login`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pwd})});
  if(!res.ok) throw new Error("Login failed");
  BDUP_TOKEN = (await res.json()).token; return BDUP_TOKEN;
}
document.getElementById('bdup_btn').onclick = async () => {
  const msg = document.getElementById('bdup_msg'); msg.textContent='';
  const src = document.getElementById('bdup_src').value.trim();
  const dst = document.getElementById('bdup_dst').value.split(/\\r?\\n/).map(s=>s.trim()).filter(Boolean);
  const overwrite = document.getElementById('bdup_overwrite').checked;
  const copy_fp = document.getElementById('bdup_copy_fp').checked;
  const copy_src = document.getElementById('bdup_copy_src').checked;
  if(!src || !dst.length){ msg.textContent='Enter source and at least one destination'; return; }
  try{
    if(!BDUP_TOKEN) await bdup_login();
    const res = await fetch(`${BACKEND}/admin/duplicate/bulk`, {
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+BDUP_TOKEN},
      body: JSON.stringify({src_key:src, dst_keys:dst, overwrite:overwrite, copy_fees_processing:copy_fp, copy_sources:copy_src})
    });
    if(!res.ok){ msg.textContent='Bulk duplicate failed: '+(await res.text()); return; }
    const data = await res.json();
    msg.textContent = `Done ✔ Created/Updated: ${data.created_or_updated.length}, Skipped: ${data.skipped.length}`;
  }catch(e){ console.error(e); msg.textContent='Bulk duplicate failed'; }
};
</script>
"""
    html = html.replace("</body>", js + "\n</body>")

with open(ADMIN, "w", encoding="utf-8") as f:
    f.write(html)

print("v3.8 Bulk Duplicate added.")
