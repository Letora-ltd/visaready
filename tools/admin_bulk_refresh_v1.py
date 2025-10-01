import os, sys

ADMIN = os.path.join("frontend","admin","index.html")

if not os.path.exists(ADMIN):
    print(f"ERROR: not found: {ADMIN}")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

# If already injected, do nothing
if "/* v-bulk-refresh */" in html:
    print("Bulk refresh already injected. Nothing to do.")
    sys.exit(0)

# Guarantee BACKEND const (won’t duplicate if present earlier)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

injection = r"""
<!-- v-bulk-refresh -->
<script>
/* v-bulk-refresh */
(function(){
  // Add a button to the Search & Filters card that bulk-sets last_verified = today
  function ensureBulkButton(){
    const card = document.getElementById('keySearchCard');
    if (!card) return;
    if (document.getElementById('ks_bulk_today')) return; // already added

    const row = document.createElement('div');
    row.style.marginTop = '10px';
    row.style.display = 'flex';
    row.style.gap = '8px';
    row.style.flexWrap = 'wrap';

    row.innerHTML = `
      <button class="btn" id="ks_bulk_today">Set last_verified = today (for filtered rows)</button>
      <span id="ks_bulk_msg" class="small"></span>
    `;
    card.appendChild(row);

    document.getElementById('ks_bulk_today').onclick = handleBulkToday;
  }

  // Helpers: reuse your auth if present, else minimal fallback using the Validate password box
  async function ensureValToken(){
    if (window.VAL_TOKEN) return window.VAL_TOKEN;
    const pwdEl = document.getElementById('val_pwd') || document.getElementById('password');
    const pwd = pwdEl ? (pwdEl.value||'').trim() : '';
    if (!pwd) { alert('Enter Admin password (Validate card) and try again.'); throw new Error('No password'); }
    const r = await fetch(`${BACKEND}/admin/login`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ password: pwd })
    });
    if (!r.ok) throw new Error('Login failed');
    const tok = (await r.json()).token;
    window.VAL_TOKEN = tok; window.token = tok;
    return tok;
  }

  async function authed(url, opts={}, relogin=true){
    if (typeof window.authedFetch === 'function') return window.authedFetch(url, opts, relogin);
    await ensureValToken();
    const headers = Object.assign({}, opts.headers||{}, { 'Authorization':'Bearer '+window.VAL_TOKEN });
    let res = await fetch(url, Object.assign({}, opts, { headers }));
    if (res.status === 401 && relogin){
      window.VAL_TOKEN = null; await ensureValToken();
      const headers2 = Object.assign({}, opts.headers||{}, { 'Authorization':'Bearer '+window.VAL_TOKEN });
      res = await fetch(url, Object.assign({}, opts, { headers: headers2 }));
    }
    return res;
  }

  function parseDate(dstr){
    if(!dstr) return null;
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dstr.trim());
    if(!m) return null;
    const dt = new Date(Date.UTC(+m[1], +m[2]-1, +m[3]));
    return isNaN(dt.getTime()) ? null : dt;
  }

  // Recompute the current filtered set (mirrors your applyFilters logic)
  function currentFilteredKeys(){
    const q = (document.getElementById('ks_q')?.value || '').toLowerCase().trim();
    const o = (document.getElementById('ks_origin')?.value || '').toUpperCase().trim();
    const d = (document.getElementById('ks_dest')?.value || '').toUpperCase().trim();
    const p = (document.getElementById('ks_purpose')?.value || '').toUpperCase().trim();
    const outdatedOnly = !!document.getElementById('ks_outdated_only')?.checked;

    let rows = (window.__ALL_KEYS__ || []).slice();
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
    return rows.map(r => r.key);
  }

  function splitKey(k){
    // "IN->DE::TOURIST" => {origin,dest,purpose}
    const [corr, purpose] = String(k||'').split('::');
    const [origin, dest] = (corr||'').split('->');
    return { origin:(origin||'').toUpperCase(), dest:(dest||'').toUpperCase(), purpose:(purpose||'').toUpperCase() };
  }

  async function fetchChecklist(key){
    const {origin,dest,purpose} = splitKey(key);
    const url = `${BACKEND}/api/checklist?origin=${encodeURIComponent(origin)}&dest=${encodeURIComponent(dest)}&category=${encodeURIComponent(purpose)}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`Fetch failed for ${key}: ${r.status}`);
    return await r.json();
  }

  async function putChecklist(key, data){
    const payload = { key, data };
    const r = await authed(`${BACKEND}/admin/checklists`, {
      method:'PUT',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify(payload)
    });
    if (!r.ok) throw new Error(`PUT failed for ${key}: ${await r.text()}`);
    return await r.json();
  }

  function todayStr(){
    const t = new Date();
    const y = t.getUTCFullYear();
    const m = String(t.getUTCMonth()+1).padStart(2,'0');
    const d = String(t.getUTCDate()).padStart(2,'0');
    return `${y}-${m}-${d}`;
  }

  async function handleBulkToday(){
    const msg = document.getElementById('ks_bulk_msg');
    msg.textContent = '';
    let keys = currentFilteredKeys();
    if (!keys.length){ msg.textContent = 'No filtered rows to update.'; return; }

    const ok = window.confirm(`Update last_verified = ${todayStr()} for ${keys.length} key(s)?`);
    if (!ok) return;

    try{
      await ensureValToken();
    }catch(e){
      msg.textContent = 'Login required: enter password in Validate card.'; return;
    }

    let done=0, errs=0;
    const BATCH = 4;
    const chunks = [];
    for (let i=0;i<keys.length;i+=BATCH) chunks.push(keys.slice(i,i+BATCH));

    for (const chunk of chunks){
      await Promise.all(chunk.map(async (key)=>{
        try{
          const current = await fetchChecklist(key);
          const updated = Object.assign({}, current, { last_verified: todayStr() });
          await putChecklist(key, updated);
          done++;
          msg.textContent = `Progress: ${done}/${keys.length} updated…`;
        }catch(e){
          console.error(e);
          errs++;
          msg.textContent = `Progress: ${done}/${keys.length} updated… (${errs} failed)`;
        }
      }));
    }

    msg.textContent = `Done ✔ Updated: ${done}, Failed: ${errs}. Refreshing table…`;

    // Refresh cache & table
    try{
      const res = await authed(`${BACKEND}/admin/checklists`, { method:'GET' });
      if (res.ok){
        const data = await res.json();
        // If your normalizeKeyRow is already present, reuse; else minimal recalc
        window.__ALL_KEYS__ = Object.entries(data).map(([k,v])=>{
          const [corr="", purRaw=""] = String(k||"").split("::");
          const [origin="", dest=""] = corr.split("->");
          const last = (v&&v.last_verified)||"—";
          const dt = parseDate(last);
          let parsed=-1, outd=true;
          if (dt){
            const t = new Date();
            const todayUTC = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate()));
            const diff = Math.floor((todayUTC.getTime()-dt.getTime())/(24*3600*1000));
            outd = diff > 90; parsed = dt.getTime();
          }
          return { key:k, origin:origin.toUpperCase(), dest:dest.toUpperCase(), purpose:purRaw.toUpperCase(), last_verified:last, _parsedDate:parsed, _outdated:outd };
        });
        // Reapply filters if available
        if (typeof window.applyFilters === 'function') window.applyFilters();
      }
    }catch(e){ console.error('post-refresh failed', e); }

  }

  document.addEventListener('DOMContentLoaded', ensureBulkButton);
})();
</script>
"""

html = html.replace("</body></html>", injection + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Bulk last_verified updater injected. Reload /admin, log in, filter, then click the new button.")
