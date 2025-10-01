import os

ADMIN = os.path.join("frontend","admin","index.html")

with open(ADMIN, "r", encoding="utf-8") as f:
    html = f.read()

# Append a self-contained script that augments the existing Search & Filters UI.
# It adds "Sort" and "Show outdated only", computes 90-day freshness, and
# overrides normalizeKeyRow/applyFilters/renderKeysTable safely (redefines them later on the page).
augment = r"""
<script>
// --- v47: Sorting + Outdated badge (90 days) ---

(function(){
  const OUTDATED_DAYS = 90;

  function parseDate(dstr){
    if(!dstr) return null;
    // Allow YYYY-MM-DD only
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dstr.trim());
    if(!m) return null;
    const y=+m[1], mo=+m[2]-1, d=+m[3];
    const dt = new Date(Date.UTC(y,mo,d));
    return isNaN(dt.getTime()) ? null : dt;
  }

  function daysBetween(a, b){
    const MS = 24*3600*1000;
    return Math.floor((b.getTime()-a.getTime())/MS);
  }

  // Inject Sort + Outdated controls into the Search card (if present)
  function ensureSortUi(){
    const card = document.getElementById("keySearchCard");
    if(!card || document.getElementById("ks_sort")) return;

    const wrap = document.createElement("div");
    wrap.className = "grid";
    wrap.style.marginTop = "10px";
    wrap.innerHTML = `
      <div>
        <div class="label">Sort</div>
        <select id="ks_sort" class="select">
          <option value="key_asc">Key ↑</option>
          <option value="key_desc">Key ↓</option>
          <option value="origin_asc">Origin ↑</option>
          <option value="origin_desc">Origin ↓</option>
          <option value="dest_asc">Destination ↑</option>
          <option value="dest_desc">Destination ↓</option>
          <option value="purpose_asc">Purpose ↑</option>
          <option value="purpose_desc">Purpose ↓</option>
          <option value="date_desc" selected>Last verified (new → old)</option>
          <option value="date_asc">Last verified (old → new)</option>
        </select>
      </div>
      <div>
        <div class="label">Freshness</div>
        <label style="display:inline-flex;align-items:center;gap:8px;">
          <input type="checkbox" id="ks_outdated_only">
          Show outdated only (>{OUTDATED_DAYS}d or missing)
        </label>
      </div>
    `;
    card.appendChild(wrap);

    // Wire events
    document.getElementById("ks_sort").addEventListener("change", () => window.applyFilters && window.applyFilters());
    document.getElementById("ks_outdated_only").addEventListener("change", () => window.applyFilters && window.applyFilters());
  }

  // --- Enhance/override normalizers & renderers safely ---
  // Keep a reference to any previous implementation
  const _oldNormalize = window.normalizeKeyRow;
  const _oldRender = window.renderKeysTable;
  const _oldApply = window.applyFilters;

  // Redefine normalizeKeyRow to compute parsed date + outdated flag
  window.normalizeKeyRow = function kvNormalize(entry){
    let row = _oldNormalize ? _oldNormalize(entry) : (function(){
      const [k,v] = entry;
      const parts = (k||"").split("::");
      const corr = parts[0] || "";
      const purpose = (parts[1] || "").toUpperCase();
      const [origin, dest] = corr.split("->");
      return {
        key: k,
        origin: (origin||"").toUpperCase(),
        dest: (dest||"").toUpperCase(),
        purpose,
        last_verified: v && v.last_verified || "—"
      };
    })();

    const dt = parseDate(row.last_verified);
    const today = new Date(); // local ok; just relative days
    let outdated = true;
    if (dt) {
      const diff = Math.abs(daysBetween(dt, new Date(Date.UTC(today.getUTCFullYear(),today.getUTCMonth(),today.getUTCDate()))));
      outdated = diff > OUTDATED_DAYS;
    }
    row._parsedDate = dt ? dt.getTime() : -1; // for stable sorting
    row._outdated = outdated;
    return row;
  };

  // Redefine render to show an "outdated" badge next to date
  window.renderKeysTable = function kvRender(rows){
    const body = document.getElementById("keysBody");
    if(!body) return;
    body.innerHTML = "";
    rows.forEach(r => {
      const tr = document.createElement("tr");
      const td1 = document.createElement("td");
      td1.textContent = r.key;

      const td2 = document.createElement("td");
      const spanDate = document.createElement("span");
      spanDate.textContent = r.last_verified || "—";
      td2.appendChild(spanDate);

      if (r._outdated) {
        const badge = document.createElement("span");
        badge.textContent = "  ⚠ outdated";
        badge.className = "small";
        badge.style.color = "#b91c1c";
        badge.style.marginLeft = "8px";
        td2.appendChild(badge);
      }

      tr.appendChild(td1);
      tr.appendChild(td2);
      body.appendChild(tr);
    });
  };

  // Sorting helper
  function sortRows(rows, mode){
    const [field, dir] = mode.split("_"); // key|origin|dest|purpose|date  + asc|desc
    const mul = (dir === "desc") ? -1 : 1;
    return rows.slice().sort((a,b)=>{
      let va, vb;
      if (field === "date") { va = a._parsedDate; vb = b._parsedDate; }
      else if (field in a) { va = (a[field]||""); vb = (b[field]||""); }
      else { va = (a.key||""); vb = (b.key||""); }
      if (va < vb) return -1*mul;
      if (va > vb) return 1*mul;
      return 0;
    });
  }

  // Redefine applyFilters to include "outdated only" + sorting
  window.applyFilters = function kvApply(){
    try{
      const q = (document.getElementById("ks_q")?.value || "").toLowerCase().trim();
      const o = (document.getElementById("ks_origin")?.value || "").toUpperCase().trim();
      const d = (document.getElementById("ks_dest")?.value || "").toUpperCase().trim();
      const p = (document.getElementById("ks_purpose")?.value || "").toUpperCase().trim();
      const outdatedOnly = !!document.getElementById("ks_outdated_only")?.checked;
      const sortMode = document.getElementById("ks_sort")?.value || "date_desc";

      let rows = (window.__ALL_KEYS__ || []);

      if (o) rows = rows.filter(r => r.origin === o);
      if (d) rows = rows.filter(r => r.dest === d);
      if (p) rows = rows.filter(r => r.purpose === p);
      if (outdatedOnly) rows = rows.filter(r => r._outdated);

      if (q) {
        rows = rows.filter(r =>
          (r.key||"").toLowerCase().includes(q) ||
          (r.purpose||"").toLowerCase().includes(q) ||
          (r.origin||"").toLowerCase().includes(q) ||
          (r.dest||"").toLowerCase().includes(q) ||
          (r.last_verified||"").toLowerCase().includes(q)
        );
      }

      rows = sortRows(rows, sortMode);
      window.renderKeysTable(rows);
    }catch(e){
      console.error("applyFilters error", e);
      // fallback to previous implementation if any
      if (_oldApply) try { _oldApply(); } catch(_){}
    }
  };

  // Initialize UI if card exists
  document.addEventListener("DOMContentLoaded", ensureSortUi);
})();
</script>
"""

# Append once if not already present
if "v47: Sorting + Outdated badge" not in html:
    html = html.replace("</body>", augment + "\n</body>")

with open(ADMIN, "w", encoding="utf-8") as f:
    f.write(html)

print("v47: Admin sorting + 'outdated' badge added.")
