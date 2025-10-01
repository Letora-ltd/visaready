import os

ADMIN = os.path.join("frontend","admin","index.html")

with open(ADMIN, "r", encoding="utf-8") as f:
    html = f.read()

if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

if 'id="keyBuilderCard"' not in html:
    card = """
<section class="card" id="keyBuilderCard">
  <h2 class="h2">Key Builder</h2>
  <p class="small">Pick Origin, Destination, Purpose — we’ll build the key string for you.</p>
  <div class="grid">
    <div><div class="label">Origin</div><select id="kb_origin" class="select"></select></div>
    <div><div class="label">Destination</div><select id="kb_dest" class="select"></select></div>
    <div><div class="label">Purpose</div>
      <select id="kb_purpose" class="select">
        <option value="TOURIST">TOURIST</option>
        <option value="STUDENT">STUDENT</option>
        <option value="WORK">WORK</option>
        <option value="FAMILY">FAMILY</option>
        <option value="TRANSIT">TRANSIT</option>
      </select>
    </div>
  </div>
  <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
    <button class="btn" id="kb_build">Build Key</button>
    <input id="kb_out" readonly class="select" style="max-width:420px;">
    <button class="btn" id="kb_copy">Copy</button>
    <span class="small">Tip: paste into Inline Editor / Duplicate cards.</span>
  </div>
</section>
"""
    html = html.replace("</main>", card + "\n</main>")

js = """
<script>
async function kb_loadCountries(){
  const o = document.getElementById('kb_origin');
  const d = document.getElementById('kb_dest');
  o.innerHTML=''; d.innerHTML='';
  const res = await fetch(`${BACKEND}/api/countries`);
  const arr = await res.json();
  arr.forEach(c=>{
    const op1=document.createElement('option'); op1.value=c.iso2; op1.textContent=`${c.name} (${c.iso2})`; o.appendChild(op1);
    const op2=document.createElement('option'); op2.value=c.iso2; op2.textContent=`${c.name} (${c.iso2})`; d.appendChild(op2);
  });
  // defaults
  const idxIN=[...o.options].findIndex(x=>x.value==='IN'); if(idxIN>=0) o.selectedIndex=idxIN;
  const idxDE=[...d.options].findIndex(x=>x.value==='DE'); if(idxDE>=0) d.selectedIndex=idxDE;
}
document.getElementById('kb_build').onclick=()=>{
  const o=document.getElementById('kb_origin').value;
  const d=document.getElementById('kb_dest').value;
  const p=document.getElementById('kb_purpose').value;
  document.getElementById('kb_out').value = `${o}->${d}::${p}`;
};
document.getElementById('kb_copy').onclick=()=>{
  const el=document.getElementById('kb_out'); el.select(); document.execCommand('copy');
};
kb_loadCountries();
</script>
"""
if "kb_loadCountries()" not in html:
    html = html.replace("</body>", js + "\n</body>")

with open(ADMIN, "w", encoding="utf-8") as f:
    f.write(html)

print("v3.9 Key Builder added.")
