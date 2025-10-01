import os, re, sys

ADMIN = os.path.join("frontend","admin","index.html")

if not os.path.exists(ADMIN):
    print(f"ERROR: not found: {ADMIN}")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

# If already injected, exit gracefully
if "/* v47-admin-ui-upgrade */" in html:
    print("v47 already injected. Nothing to do.")
    sys.exit(0)

# Ensure there's a BACKEND const somewhere (light guard; no duplicate if already present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

# Inject a runtime script that:
# - Inserts the Search & Filters card right before the "Existing Keys" h3
# - Overrides loadKeys() after page scripts load (so the Login flow continues to work)
# - Adds sorting + outdated logic
injection = r"""
<!-- v47 admin UI upgrade -->
<script>
/* v47-admin-ui-upgrade */
(function(){
  const OUTDATED_DAYS = 90;

  function ensureSearchCard(){
    // Find "Existing Keys" header; insert our card before it
    const h3s = Array.from(document.querySelectorAll('h3.h2'));
    const target = h3s.find(h => h.textContent.trim().toLowerCase() === 'existing keys');
    if (!target) return false;
    if (document.getElementById('keySearchCard')) return true; // already injected

    const wrap = document.createElement('section');
    wrap.className = 'card';
    wrap.id = 'keySearchCard';
    wrap.innerHTML = `
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
      <div class="grid" style="margin-top:10px;">
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
            Show outdated only (>90d or missing)
          </label>
        </div>
      </div>
    `;
    target.parentNode.insertBefore(wrap, target);
    return true;
  }

  function parseDate(dstr){
    if(!dstr) return null;
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dstr.trim());
    if(!m) return null;
    const dt = new Date(Date.UTC(+m[1], +m[2]-1, +m[3]));
    return isNaN(dt.getTime()) ? null : dt;
  }

  function normalizeRow([k, v]){
    const [corr="", purRaw=""] = String(k||"").split("::");
    const [origin="", dest=""] = corr.split("->");
    const purpose = purRaw.toUpperCase();
    const last_verified = (v && v.last_verified) || "—";
    const mdt = parseDate(last_verified);
    let parsed = -1, outdated = true;
    if (mdt){
      const today = new Date();
      const todayUTC = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
      const diff = Math.floor((todayUTC.getTime() - mdt.getTime()) / (24*3600*1000));
      outdated = diff > OUTDATED_DAYS;
      parsed = mdt.getTime();
    }
    return {
      key: k,
      origin: origin.toUpperCase(),
      dest: dest.toUpperCase(),
      purpose,
      last_verified,
      _parsedDate: parsed,
      _outdated: outdated
    };
  }

  function renderRows(rows){
    const body = document.getElementById('keysBody');
    if(!body) return;
    body.innerHTML = '';
    rows.forEach(r=>{
      const tr = document.createElement('tr');
      const td1 = document.createElement('td'); td1.textContent = r.key;
      const td2 = document.createElement('td');
      const span = document.createElement('span'); span.textContent = r.last_verified || '—';
      td2.appendChild(span);
      if (r._outdated){
        const badge = document.createElement('span');
        badge.textContent = '  ⚠ outdated';
        badge.className = 'small';
        badge.style.color = '#b91c1c';
        badge.style.marginLeft = '8px';
        td2.appendChild(badge);
      }
      tr.appendChild(td1); tr.appendChild(td2); body.appendChild(tr);
    });
  }

  function sortRows(rows, mode){
    const [field, dir] = (mode||'date_desc').split('_');
    const mul = (dir==='desc') ? -1 : 1;
    return rows.slice().sort((a,b)=>{
      let va, vb;
      if (field==='date'){ va=a._parsedDate; vb=b._parsedDate; }
      else if (field in a){ va=(a[field]||''); vb=(b[field]||''); }
      else { va=(a.key||''); vb=(b.key||''); }
      if (va<vb) return -1*mul; if (va>vb) return 1*mul; return 0;
    });
  }

  function applyFilters(){
    const q = (document.getElementById('ks_q')?.value || '').toLowerCase().trim();
    const o = (document.getElementById('ks_origin')?.value || '').toUpperCase().trim();
    const d = (document.getElementById('ks_dest')?.value || '').toUpperCase().trim();
    const p = (document.getElementById('ks_purpose')?.value || '').toUpperCase().trim();
    const outdatedOnly = !!document.getElementById('ks_outdated_only')?.checked;
    const sortMode = document.getElementById('ks_sort')?.value || 'date_desc';

    let rows = window.__ALL_KEYS__ || [];
    if (o) rows = rows.filter(r=>r.origin===o);
    if (d) rows = rows.filter(r=>r.dest===d);
    if (p) rows = rows.filter(r=>r.purpose===p);
    if (outdatedOnly) rows = rows.filter(r=>r._outdated);
    if (q){
      rows = rows.filter(r =>
        (r.key||'').toLowerCase().includes(q) ||
        (r.purpose||'').toLowerCase().includes(q) ||
        (r.origin||'').toLowerCase().includes(q) ||
        (r.dest||'').toLowerCase().includes(q) ||
        (r.last_verified||'').toLowerCase().includes(q)
      );
    }
    rows = sortRows(rows, sortMode);
    renderRows(rows);
  }

  function wireFilterEvents(){
    ['ks_q','ks_origin','ks_dest','ks_purpose','ks_sort','ks_outdated_only'].forEach(id=>{
      const el = document.getElementById(id);
      if(!el) return;
      el.addEventListener('input', applyFilters);
      el.addEventListener('change', applyFilters);
    });
  }

  // Override/augment loadKeys() after page scripts are parsed
  const _origLoadKeys = window.loadKeys;
  window.loadKeys = async function(){
    try{
      if (typeof _origLoadKeys === 'function'){
        // We fetch ourselves (to build the cache) instead of calling the old renderer
        // because we need to normalize & filter.
      }
      // token variable is already set by the Login button script
      const res = await fetch(`${BACKEND}/admin/checklists`, { headers: { "Authorization": "Bearer " + (window.token||'') }});
      const data = await res.json();
      window.__ALL_KEYS__ = Object.entries(data).map(normalizeRow);

      ensureSearchCard();
      wireFilterEvents();
      applyFilters(); // renders table with filters/sorting

    }catch(e){
      console.error('loadKeys (v47) failed; falling back', e);
      if (typeof _origLoadKeys === 'function') return _origLoadKeys();
    }
  };

  // If the editor is already visible (user previously logged in), try to mount UI
  document.addEventListener('DOMContentLoaded', ()=>{
    ensureSearchCard();
  });
})();
</script>
"""

# Insert the injection right before </body> to avoid touching existing code order
html = html.replace("</body></html>", injection + "\n</body></html>")

# Write back
open(ADMIN, "w", encoding="utf-8").write(html)
print("v47 admin search+filters+sorting injected. Reload /admin, log in, and enjoy.")
