import os, re, textwrap

BACKEND = os.path.join("backend")
FRONTEND = os.path.join("frontend")
APP = os.path.join(BACKEND, "app.py")
VALIDATE_MOD = os.path.join(BACKEND, "admin_validate.py")
CSV_HTML = os.path.join(FRONTEND, "admin", "csv.html")
ADMIN_HTML = os.path.join(FRONTEND, "admin", "index.html")

# ---------- 1) Backend: admin_validate.py ----------
validate_code = textwrap.dedent("""
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
""").lstrip()

os.makedirs(BACKEND, exist_ok=True)
with open(VALIDATE_MOD, "w", encoding="utf-8") as f:
    f.write(validate_code)

# ---------- 2) Patch backend/app.py to include validate router ----------
with open(APP, "r", encoding="utf-8") as f:
    app_src = f.read()

if "include_router(admin_validate.router)" not in app_src:
    if "from . import admin_validate" not in app_src:
        app_src += "\ntry:\n    from . import admin_validate\nexcept Exception:\n    import admin_validate\n"
    app_src += "app.include_router(admin_validate.router)\n"
    with open(APP, "w", encoding="utf-8") as f:
        f.write(app_src)

# ---------- 3) Frontend: CSV page - Sample CSV UI ----------
if os.path.exists(CSV_HTML):
    html = open(CSV_HTML, "r", encoding="utf-8").read()

    # ensure BACKEND const
    if "const BACKEND" not in html:
        html = html.replace("<script>", "<script>\n  const BACKEND = 'http://127.0.0.1:8000';", 1)

    # add sample block if missing
    if 'id="sampleKey"' not in html:
        sample_block = """
  <section class="card">
    <h2 class="h2">Sample CSV</h2>
    <div class="grid">
      <div>
        <div class="label">Key (optional: build a one-row sample from this key)</div>
        <input id="sampleKey" placeholder="IN->DE::TOURIST">
      </div>
    </div>
    <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap;">
      <button class="btn" id="btnSampleBlank">Download Blank Template (Friendly)</button>
      <button class="btn" id="btnSampleFromKey">Download Sample From Key</button>
      <span id="sampleMsg" class="small"></span>
    </div>
  </section>
"""
        html = html.replace("</main>", sample_block + "\n</main>")

    # add JS handlers (only once)
    if "function downloadCsvBlob(" not in html:
        js = """
<script>
function downloadCsvBlob(filename, rows){
  const esc = v => typeof v === 'string' ? `"${v.replaceAll('"','""')}"` : (v ?? '');
  const csv = rows.map(r => r.map(esc).join(',')).join('\\n');
  const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

document.getElementById('btnSampleBlank').onclick = () => {
  const header = ["key","last_verified","fees","processing","items_text","sources_text"];
  const row = ["ORIGIN->DEST::PURPOSE","","","","Title :: Details","Label :: URL"];
  downloadCsvBlob("visaready_sample_blank.csv", [header, row]);
};

document.getElementById('btnSampleFromKey').onclick = async () => {
  const key = document.getElementById('sampleKey').value.trim();
  const msg = document.getElementById('sampleMsg');
  msg.textContent = '';
  if(!key){ msg.textContent = 'Enter a key or use Blank Template.'; return; }
  try{
    const [corr, purpose] = key.split('::');
    const [origin, dest] = (corr||'').split('->');
    const url = `${BACKEND}/api/checklist?origin=${encodeURIComponent(origin)}&dest=${encodeURIComponent(dest)}&category=${encodeURIComponent(purpose)}`;
    const res = await fetch(url);
    if(!res.ok){ msg.textContent = 'Key not found'; return; }
    const data = await res.json();
    const header = ["key","last_verified","fees","processing","items_text","sources_text"];
    const items_text = (data.items||[]).map(it => `${it.title||''} :: ${it.details||''}${it.source_url? ' :: '+it.source_url:''}`).join('\\n');
    const sources_text = (data.sources||[]).map(s => `${s.label||''} :: ${s.url||''}`).join('\\n');
    const row = [key, data.last_verified||'', data.fees||'', data.processing||'', items_text, sources_text];
    downloadCsvBlob(`visaready_sample_${origin}_${dest}_${purpose}.csv`, [header, row]);
  }catch(e){ console.error(e); msg.textContent='Failed to build sample.'; }
};
</script>
"""
        html = html.replace("</body>", js + "\n</body>")

    with open(CSV_HTML, "w", encoding="utf-8") as f:
        f.write(html)

# ---------- 4) Frontend Admin: Validate All card ----------
if os.path.exists(ADMIN_HTML):
    ahtml = open(ADMIN_HTML, "r", encoding="utf-8").read()

    if "const BACKEND" not in ahtml:
        ahtml = ahtml.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

    if 'id="validateCard"' not in ahtml:
        card = """
<section class="card" id="validateCard">
  <h2 class="h2">Validate All Checklists</h2>
  <p class="small">Runs a static check for missing fields, empty items, and malformed URLs.</p>
  <div class="grid">
    <div><div class="label">Admin Password</div><input id="val_pwd" type="password" placeholder="Enter admin password"></div>
  </div>
  <div style="margin-top:10px;">
    <button class="btn" id="val_btn">Run Validation</button>
    <span id="val_msg" class="small" style="margin-left:10px;"></span>
  </div>
  <div id="val_out" class="small" style="margin-top:10px;"></div>
</section>
"""
        ahtml = ahtml.replace("</main>", card + "\n</main>")

    if "function val_login(" not in ahtml:
        js = """
<script>
let VAL_TOKEN=null;
async function val_login(){
  const pwd = document.getElementById('val_pwd').value.trim();
  if(!pwd) throw new Error("Enter admin password");
  const res = await fetch(`${BACKEND}/admin/login`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pwd})});
  if(!res.ok) throw new Error("Login failed");
  VAL_TOKEN = (await res.json()).token; return VAL_TOKEN;
}
document.getElementById('val_btn').onclick = async () => {
  const msg=document.getElementById('val_msg'); const out=document.getElementById('val_out');
  msg.textContent=''; out.textContent='';
  try{
    if(!VAL_TOKEN) await val_login();
    const res = await fetch(`${BACKEND}/admin/validate`, { headers:{'Authorization':'Bearer '+VAL_TOKEN} });
    if(!res.ok){ msg.textContent='Validation failed: '+(await res.text()); return; }
    const data = await res.json();
    msg.textContent = `Issues found: ${data.count}`;
    if(data.count===0){ out.textContent='All good ✔'; return; }
    const lines = data.issues.map(i => `• ${i.key} — ${i.issue}`);
    out.textContent = lines.join('\\n');
  }catch(e){ console.error(e); msg.textContent='Validation failed'; }
};
</script>
"""
        ahtml = ahtml.replace("</body>", js + "\n</body>")

    with open(ADMIN_HTML, "w", encoding="utf-8") as f:
        f.write(ahtml)

print("v4.2 Sample CSV (blank/from key) + Validate All added.")
