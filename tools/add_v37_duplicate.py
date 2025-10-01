import os, re

APP = os.path.join("backend","app.py")
ADMIN = os.path.join("frontend","admin","index.html")

# ---------- Patch backend/app.py: add /admin/duplicate ----------
with open(APP, "r", encoding="utf-8") as f:
    src = f.read()

if "/admin/duplicate" not in src:
    block = r"""
# -------- Duplicate corridor --------
class DuplicateIn(BaseModel):
    src_key: str
    dst_key: str
    overwrite: bool = False
    copy_fees_processing: bool = True
    copy_sources: bool = True

@app.post("/admin/duplicate")
def admin_duplicate(payload: DuplicateIn, authorization: str | None = Header(default=None)):
    _auth(authorization)

    def split_key(k: str):
        # expects ORIGIN->DEST::PURPOSE
        if "::" not in k or "->" not in k:
            raise HTTPException(400, "Bad key format; expected ORIGIN->DEST::PURPOSE")
        corr, purpose = k.split("::", 1)
        origin, dest = corr.split("->", 1)
        return origin.upper(), dest.upper(), purpose.upper()

    # Load and validate
    data = load_json("checklists.json")
    if payload.src_key not in data:
        # try normalized case-match
        o, d, p = split_key(payload.src_key)
        norm_src = f"{o}->{d}::{p}"
        if norm_src not in data:
            raise HTTPException(404, f"Source key not found: {payload.src_key}")
        payload.src_key = norm_src

    o2, d2, p2 = split_key(payload.dst_key)
    dst_key = f"{o2}->{d2}::{p2}"

    if (not payload.overwrite) and dst_key in data:
        raise HTTPException(409, f"Destination key exists: {dst_key}. Enable overwrite to replace.")

    src_entry = data[payload.src_key]
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
    save_json("checklists.json", data)
    return {"ok": True, "dst_key": dst_key}
"""
    # inject before the CSV router include (already at bottom of file)
    # If not found, just append at end
    insertion_point = src.rfind("app.include_router(admin_csv.router)")
    if insertion_point != -1:
        src = src[:insertion_point] + block + "\n" + src[insertion_point:]
    else:
        src = src + "\n" + block

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

# ---------- Patch frontend/admin/index.html: add Duplicate card + JS ----------
with open(ADMIN, "r", encoding="utf-8") as f:
    html = f.read()

# BACKEND const (if not present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

if 'id="dupCard"' not in html:
    card = """
<section class="card" id="dupCard">
  <h2 class="h2">Duplicate Corridor</h2>
  <p class="small">Clone an existing key (items + optional fees/processing/sources) to a new key.</p>
  <div class="grid">
    <div>
      <div class="label">Source key (e.g., IN-&gt;DE::TOURIST)</div>
      <input id="dup_src" placeholder="IN->DE::TOURIST" />
    </div>
    <div>
      <div class="label">Destination key</div>
      <input id="dup_dst" placeholder="IN->FR::TOURIST" />
    </div>
    <div>
      <div class="label">Admin Password</div>
      <input id="dup_pwd" type="password" placeholder="Enter admin password" />
    </div>
  </div>
  <div style="margin-top:10px; display:flex; gap:12px; flex-wrap:wrap;">
    <label style="display:inline-flex;align-items:center;gap:6px;">
      <input type="checkbox" id="dup_overwrite"> Overwrite if exists
    </label>
    <label style="display:inline-flex;align-items:center;gap:6px;">
      <input type="checkbox" id="dup_copy_fp" checked> Copy fees & processing
    </label>
    <label style="display:inline-flex;align-items:center;gap:6px;">
      <input type="checkbox" id="dup_copy_src" checked> Copy sources
    </label>
    <button class="btn" id="dup_btn">Duplicate</button>
    <span id="dup_msg" class="small"></span>
  </div>
</section>
"""
    html = html.replace("</main>", card + "\n</main>")

# Add JS handler
if "function dup_login(" not in html:
    js = """
<script>
let DUP_TOKEN = null;

async function dup_login() {
  const pwd = document.getElementById('dup_pwd').value.trim();
  if(!pwd) throw new Error("Enter admin password");
  const res = await fetch(`${BACKEND}/admin/login`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ password: pwd })
  });
  if(!res.ok) throw new Error("Login failed: " + await res.text());
  DUP_TOKEN = (await res.json()).token;
  return DUP_TOKEN;
}

document.getElementById('dup_btn').onclick = async () => {
  const msg = document.getElementById('dup_msg');
  msg.textContent = '';
  const src = document.getElementById('dup_src').value.trim();
  const dst = document.getElementById('dup_dst').value.trim();
  const overwrite = document.getElementById('dup_overwrite').checked;
  const copy_fp = document.getElementById('dup_copy_fp').checked;
  const copy_src = document.getElementById('dup_copy_src').checked;

  if(!src || !dst){ msg.textContent = 'Enter both source and destination keys'; return; }

  try {
    if(!DUP_TOKEN) await dup_login();
    const payload = {
      src_key: src,
      dst_key: dst,
      overwrite: overwrite,
      copy_fees_processing: copy_fp,
      copy_sources: copy_src
    };
    const res = await fetch(`${BACKEND}/admin/duplicate`, {
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+DUP_TOKEN},
      body: JSON.stringify(payload)
    });
    if(!res.ok){
      msg.textContent = 'Duplicate failed: ' + (await res.text());
      return;
    }
    const data = await res.json();
    msg.textContent = 'Duplicated to ' + data.dst_key + ' ✔';
  } catch(e){
    console.error(e);
    msg.textContent = 'Duplicate failed.';
  }
};
</script>
"""
    html = html.replace("</body>", js + "\n</body>")

with open(ADMIN, "w", encoding="utf-8") as f:
    f.write(html)

print("v3.7 Duplicate corridor added: backend endpoint + admin UI.")
