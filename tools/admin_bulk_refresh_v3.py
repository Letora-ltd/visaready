import os, sys

ADMIN = os.path.join("frontend","admin","index.html")

if not os.path.exists(ADMIN):
    print(f"ERROR: not found: {ADMIN}")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

# Ensure BACKEND const exists (won’t duplicate earlier definitions)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

# Remove any prior v-bulk-refresh blocks safely (string slicing, not regex)
start_tag = "<!-- v-bulk-refresh -->"
end_marker = "/* v-bulk-refresh */"
changed = False
while True:
    s = html.find(start_tag)
    if s == -1: break
    e = html.find(end_marker, s)
    if e == -1: break
    # Close the script tag after end_marker
    close_script = html.find("</script>", e)
    if close_script == -1: break
    html = html[:s] + html[close_script + len("</script>") + 1:]  # +1 to drop trailing newline if present
    changed = True

# Inject new block
injection = r"""
<!-- v-bulk-refresh -->
<script>
/* v-bulk-refresh */
(function(){
  // ------------- UI injection -------------
  function ensureBulkControls(){
    const card = document.getElementById('keySearchCard');
    if (!card) return false;

    let row = document.getElementById('ks_bulk_row');
    if (!row) {
      row = document.createElement('div');
      row.id = 'ks_bulk_row';
      row.style.marginTop = '10px';
      row.style.display = 'flex';
      row.style.gap = '8px';
      row.style.flexWrap = 'wrap';
      card.appendChild(row);
    }

    if (!document.getElementById('ks_bulk_today')){
      const btn = document.createElement('button');
      btn.id = 'ks_bulk_today';
      btn.className = 'btn';
      btn.textContent = 'Set last_verified = today (for filtered rows)';
      row.appendChild(btn);
      btn.onclick = handleBulkToday;
    }

    if (!document.getElementById('ks_bulk_batch')){
      const wrap = document.createElement('label');
      wrap.style.display = 'inline-flex';
      wrap.style.alignItems = 'center';
      wrap.style.gap = '6px';
      wrap.innerHTML = `Batch size: <input id="ks_bulk_batch" type="number" min="1" max="50" value="4" style="width:80px;">`;
      row.appendChild(wrap);
    }

    if (!document.getElementById('ks_bulk_delay')){
      const wrap = document.createElement('label');
      wrap.style.display = 'inline-flex';
      wrap.style.alignItems = 'center';
      wrap.style.gap = '6px';
      wrap.innerHTML = `Delay (ms): <input id="ks_bulk_delay" type="number" min="0" max="10000" value="200" style="width:90px;">`;
      row.appendChild(wrap);
    }

    if (!document.getElementById('ks_bulk_skip_today')){
      const wrap = document.createElement('label');
      wrap.style.display = 'inline-flex';
      wrap.style.alignItems = 'center';
      wrap.style.gap = '6px';
      wrap.innerHTML = `<input id="ks_bulk_skip_today" type="checkbox" checked> Only if not today`;
      row.appendChild(wrap);
    }

    if (!document.getElementById('ks_bulk_msg')){
      const span = document.createElement('span');
      span.id = 'ks_bulk_msg';
      span.className = 'small';
      row.appendChild(span);
    }

    return true;
  }

  // ------------- Auth/helpers -------------
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
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((dstr||'').trim());
    if(!m) return null;
    const dt = new Date(Date.UTC(+m[1], +m[2]-1, +m[3]));
    return isNaN(dt.getTime()) ? null : dt;
  }
  function todayStr(){
    const t = new Date();
    const y=t.getUTCFullYear(), m=String(t.getUTCMonth()+1).padStart(2,'0'), d=String(t.getUTCDate()).padStart(2,'0');
    return `${y}-${m}-${d}`;
  }
  function splitKey(k){
    const [corr, purpose] = String(k||'').split('::');
    const [origin, dest] = (corr||'').split('->');
    return { origin:(origin||'').toUpperCase(), dest:(dest||'').toUpperCase(), purpose:(purpose||'').toUpperCase() };
  }
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
  function sleep(ms){ return new Promise(res=>setTimeout(res, ms||0)); }

  // ------------- Bulk handler -------------
  async function handleBulkToday(){
    const msg = document.getElementById('ks_bulk_msg');
    msg.textContent = '';

    let keys = currentFilteredKeys();
    if (!keys.length){ msg.textContent = 'No filtered rows to update.'; return; }

    const batchEl = document.getElementById('ks_bulk_batch');
    const delayEl = document.getElementById('ks_bulk_delay');
    const skipTodayEl = document.getElementById('ks_bulk_skip_today');

    const BATCH = Math.max(1, Math.min(50, parseInt(batchEl?.value || '4', 10) || 4));
    const DELAY = Math.max(0, Math.min(10000, parseInt(delayEl?.value || '200', 10) || 0));
    const SKIP_TODAY = !!(skipTodayEl && skipTodayEl.checked);
    const today = todayStr();

    // If skipping rows already stamped today, pre-filter keys cheaply by cache if possible
    if (SKIP_TODAY && Array.isArray(window.__ALL_KEYS__)){
      const todayKeys = new Set(
        window.__ALL_KEYS__.filter(r => String(r.last_verified||'').trim() === today).map(r=>r.key)
      );
      keys = keys.filter(k => !todayKeys.has(k));
    }

    if (!keys.length){ msg.textContent = 'Nothing to update (already stamped today).'; return; }

    const ok = window.confirm(
      `Update last_verified = ${today} for ${keys.length} key(s)?\n\nBatch size: ${BATCH}\nDelay between batches: ${DELAY} ms\nSkip rows already today: ${SKIP_TODAY ? 'Yes' : 'No'}`
    );
    if (!ok) return;

    try{
      await ensureValToken();
    }catch(e){
      msg.textContent = 'Login required: enter password in Validate card.'; return;
    }

    let done=0, errs=0;
    for (let i=0; i<keys.length; i+=BATCH){
      const chunk = keys.slice(i, i+BATCH);
      await Promise.all(chunk.map(async (key)=>{
        try{
          const current = await fetchChecklist(key);
          if (SKIP_TODAY && String(current.last_verified||'').trim() === today) {
            // Double-check server value and skip if already today
            return;
          }
          const updated = Object.assign({}, current, { last_verified: today });
          await putChecklist(key, updated);
          done++;
        }catch(e){ console.error(e); errs++; }
      }));
      msg.textContent = `Progress: ${done}/${keys.length} updated… (${errs} failed)`;
      if (i + BATCH < keys.length && DELAY > 0) await sleep(DELAY);
    }

    msg.textContent = `Done ✔ Updated: ${done}, Failed: ${errs}. Refreshing table…`;

    // Refresh cache & table (minimal)
    try{
      const res = await authed(`${BACKEND}/admin/checklists`, { method:'GET' });
      if (res.ok){
        const data = await res.json();
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
        if (typeof window.applyFilters === 'function') window.applyFilters();
      }
    }catch(e){ console.error('post-refresh failed', e); }
  }

  document.addEventListener('DOMContentLoaded', ensureBulkControls);
})();
</script>
"""

html = html.replace("</body></html>", injection + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)

if changed:
    print("Removed previous bulk-refresh block(s).")
print("Injected bulk refresh v3 (batch size + delay + skip today). Reload /admin.")
