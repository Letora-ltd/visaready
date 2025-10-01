import os, re, json

ADMIN = os.path.join("frontend","admin","index.html")

with open(ADMIN, "r", encoding="utf-8") as f:
    html = f.read()

# 1) Insert Search & Filter UI above Existing Keys table
if 'id="keySearchCard"' not in html:
    html = html.replace(
        '<h3 class="h2">Existing Keys</h3>',
        """<section class="card" id="keySearchCard">
  <h2 class="h2">Search & Filters</h2>
  <div class="grid">
    <div>
      <div class="label">Search</div>
      <input id="ks_q" placeholder="Type to search (key, purpose, origin, destination, date)">
    </div>
    <div>
      <div class="label">Origin</div>
      <input id="ks_origin" placeholder="e.g., IN or GB">
    </div>
    <div>
      <div class="label">Destination</div>
      <input id="ks_dest" placeholder="e.g., DE or US">
    </div>
    <div>
      <div class="label">Purpose</div>
      <select id="ks_purpose" class="select">
        <option value="">All</option>
        <option value="TOURIST">TOURIST</option>
        <option value="STUDENT">STUDENT</option>
        <option value="WORK">WORK</option>
        <option value="FAMILY">FAMILY</option>
        <option value="TRANSIT">TRANSIT</option>
      </select>
    </div>
  </div>
</section>
<h3 class="h2">Existing Keys</h3>"""
    )

# 2) Wire filtering logic; keep original loadKeys but enhance it
if "function renderKeysTable(" not in html:
    script = """
<script>
let __ALL_KEYS__ = [];     // full list from /admin/checklists
let token = token || null; // reuse if present

function normalizeKeyRow([k, v]) {
  // k = "IN->DE::TOURIST"
  const parts = k.split("::");
  const corr = parts[0] || "";
  const purpose = (parts[1] || "").toUpperCase();
  const [origin, dest] = corr.split("->");
  return {
    key: k,
    origin: (origin||"").toUpperCase(),
    dest: (dest||"").toUpperCase(),
    purpose,
    last_verified: v?.last_verified || "—"
  };
}

function renderKeysTable(rows){
  const body = document.getElementById("keysBody");
  if(!body) return;
  body.innerHTML = "";
  rows.forEach(r => {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td"); td1.textContent = r.key;
    const td2 = document.createElement("td"); td2.textContent = r.last_verified || "—";
    tr.appendChild(td1); tr.appendChild(td2); body.appendChild(tr);
  });
}

function applyFilters(){
  const q = (document.getElementById("ks_q")?.value || "").toLowerCase().trim();
  const o = (document.getElementById("ks_origin")?.value || "").toUpperCase().trim();
  const d = (document.getElementById("ks_dest")?.value || "").toUpperCase().trim();
  const p = (document.getElementById("ks_purpose")?.value || "").toUpperCase().trim();

  let rows = __ALL_KEYS__;
  if (o) rows = rows.filter(r => r.origin === o);
  if (d) rows = rows.filter(r => r.dest === d);
  if (p) rows = rows.filter(r => r.purpose === p);
  if (q) {
    rows = rows.filter(r =>
      r.key.toLowerCase().includes(q) ||
      r.purpose.toLowerCase().includes(q) ||
      r.origin.toLowerCase().includes(q) ||
      r.dest.toLowerCase().includes(q) ||
      (r.last_verified||"").toLowerCase().includes(q)
    );
  }
  renderKeysTable(rows);
}

async function loadKeys(){
  // assumes token was set by Login button (editor card)
  const res = await fetch(`${BACKEND}/admin/checklists`, { headers: { "Authorization": "Bearer " + token }});
  const data = await res.json();
  __ALL_KEYS__ = Object.entries(data).map(normalizeKeyRow);
  applyFilters();
}

function wireKeyFilters(){
  ["ks_q","ks_origin","ks_dest","ks_purpose"].forEach(id=>{
    const el = document.getElementById(id);
    if(el){
      el.addEventListener("input", applyFilters);
      el.addEventListener("change", applyFilters);
    }
  });
}

// If editor is already shown, wire filters immediately
document.addEventListener("DOMContentLoaded", wireKeyFilters);
</script>
"""
    # Append before closing body
    html = html.replace("</body>", script + "\n</body>")

with open(ADMIN, "w", encoding="utf-8") as f:
    f.write(html)

print("v46: Admin search + filters added above Existing Keys.")
"""
print("v46: Admin search + filters added.")
