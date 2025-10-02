import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found"); sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-batch23 */" in html:
    print("Batch 2+3 UI already applied."); sys.exit(0)

# Ensure BACKEND const
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-batch23 -->
<style>
/* ===== Batch 2+3 UI ===== */
.vr-action-pro{display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:8px 0 12px 0}
.vr-badge-green{font-size:12px;padding:6px 10px;border-radius:999px;border:1px solid rgba(34,197,94,.4);color:#bbf7d0;background:rgba(34,197,94,.12)}
.vr-badge-warn{font-size:12px;padding:6px 10px;border-radius:999px;border:1px solid rgba(245,158,11,.4);color:#fde68a;background:rgba(245,158,11,.12)}
.vr-btn-sm{padding:8px 10px;border:none;border-radius:10px;font-weight:700;cursor:pointer;background:#A3E635;color:#07121f; box-shadow:0 8px 22px rgba(163,230,53,.3)}
.vr-btn-ghost{padding:8px 10px;border-radius:10px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.06);color:#e5f0ff}
.vr-row{display:flex; gap:8px; align-items:center; flex-wrap:wrap}
.vr-field{display:flex; gap:6px; align-items:center}
.vr-input-sm{padding:8px 10px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#e5f0ff}
.vr-list{max-height:320px; overflow:auto; padding:10px; border-radius:12px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.04)}
</style>

<script>
/* v-admin-batch23 */
(function(){

  // ---------- utilities ----------
  function toast(msg, kind='ok', ms=2400){
    let box = document.getElementById('vr_toast'); if(!box){ box=document.createElement('div'); box.id='vr_toast'; box.className='vr-toast'; document.body.appendChild(box); }
    box.className='vr-toast '+(kind==='err'?'err':(kind==='warn'?'warn':'ok'));
    box.textContent = msg; box.style.display='block';
    clearTimeout(window.__vr_toast_t); window.__vr_toast_t=setTimeout(()=>{box.style.display='none'}, ms);
  }
  const token = ()=> window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || '';

  // -------- ROLE-AWARE: hide/disable by role/scope --------
  async function roleAware(){
    try{
      const t = token(); if(!t) return;
      const r = await fetch(`${BACKEND}/auth/whoami`, { headers:{Authorization:'Bearer '+t}});
      if(!r.ok) return;
      const claims = (await r.json()).claims||{};
      const role = String(claims.role||'user').toLowerCase();
      const scope = claims.scope || {};
      const ro = !!scope.read_only;

      // If read-only → disable write buttons
      if (ro){
        ['ie_saveBtn','dup_btn','bdup_btn','val_fix_btn'].forEach(id=>{
          const el=document.getElementById(id); if(el){ el.disabled=true; el.title='Read-only role'; }
        });
      }

      // If role is plain "user", hide admin heavy sections
      if (role==='user'){
        const hideIds=['dupCard','bulkDupCard','validateCard'];
        hideIds.forEach(id=>{ const e=document.getElementById(id); if(e) e.style.display='none'; });
      }

      // Sidebar hide by role
      if (role==='user'){
        document.querySelectorAll('.vr-sidebar a[href="#dupCard"], .vr-sidebar a[href="#bulkDupCard"], .vr-sidebar a[href="#validateCard"]').forEach(a=>a.remove());
      }
    }catch(e){}
  }

  // ---------- INLINE EDITOR: Templates dropdown ----------
  function inlineTemplates(){
    const sec = document.getElementById('inlineEditor'); if(!sec) return;
    if (document.getElementById('ie_tpl')) return;
    const bar = document.createElement('div'); bar.className='vr-action-pro';
    bar.innerHTML = `
      <span class="vr-badge-green">Templates</span>
      <select id="ie_tpl" class="vr-input-sm">
        <option value="">Select template…</option>
        <option value="TOURIST">Tourist (generic)</option>
        <option value="STUDENT">Student (generic)</option>
        <option value="WORK">Work (generic)</option>
      </select>
      <button class="vr-btn-sm vr-btn-ghost" id="ie_tpl_apply">Apply to editor</button>
    `;
    sec.prepend(bar);
    const TPLS = {
      TOURIST: [
        "Valid passport :: 6+ months validity and blank pages",
        "Travel insurance :: Must cover entire stay",
        "Proof of funds :: Recent bank statements/sponsor",
        "Accommodation proof :: Hotel bookings or invitation",
        "Return ticket :: Confirmed itinerary"
      ],
      STUDENT: [
        "Admission letter :: From recognised institution",
        "Tuition fee proof :: Paid receipt/fee plan",
        "Financial proof :: Bank statements/scholarship/sponsor",
        "Accommodation :: Hostel booking/lease",
        "Insurance :: Health coverage as required"
      ],
      WORK: [
        "Employment contract :: From host-country employer",
        "Work authorisation :: Permit/sponsor approval",
        "Qualifications :: Degree, experience letters",
        "Police clearance :: If required",
        "Insurance :: Health/travel"
      ]
    };
    document.getElementById('ie_tpl_apply').onclick = ()=>{
      const type = (document.getElementById('ie_tpl')||{}).value || '';
      if(!type){ toast('Pick a template', 'warn'); return; }
      const items = TPLS[type] || [];
      const itemsText = items.join('\\n');
      const it = document.getElementById('ie_items');
      if (it){ it.value = itemsText; toast(`${type} template applied`, 'ok'); }
    };
  }

  // ---------- CSV EXPORT: filtered rows with JSON columns ----------
  function csvExportFiltered(){
    const anchor = document.getElementById('keySearchCard'); if(!anchor) return;
    if (document.getElementById('ks_export_filtered')) return;
    const row = document.createElement('div'); row.className='vr-action-pro';
    row.innerHTML = `
      <span class="vr-badge-warn">CSV</span>
      <button id="ks_export_filtered" class="vr-btn-sm">Export filtered (JSON cols)</button>
    `;
    anchor.appendChild(row);

    function currentFiltered(){
      const q = (document.getElementById('ks_q')?.value || '').toLowerCase().trim();
      const o = (document.getElementById('ks_origin')?.value || '').toUpperCase().trim();
      const d = (document.getElementById('ks_dest')?.value || '').toUpperCase().trim();
      const p = (document.getElementById('ks_purpose')?.value || '').toUpperCase().trim();
      const outdatedOnly = !!document.getElementById('ks_outdated_only')?.checked;
      let rows = (window.__ALL_KEYS__||[]).slice();
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
          (r.last_verified||'').toLowerCase().includes(q));
      }
      return rows.map(r=>r.key);
    }

    function toCSV(rows){
      const header = ["key","last_verified","fees","processing","items_json","sources_json"];
      const lines = [header.join(",")];
      rows.forEach(r=>{
        const esc = s => `"${String(s or "").replaceAll('"','""')}"`;
        lines.push(header.map(h=>esc(r[h] if h in r else "")).join(","));
      });
      return lines.join("\\n");
    }

    document.getElementById('ks_export_filtered').onclick = async ()=>{
      try{
        const keys = currentFiltered();
        if(!keys.length){ toast('No filtered rows', 'warn'); return; }
        const t = token(); if(!t){ toast('Sign in first','warn'); return; }
        // fetch full checklists once
        const res = await fetch(`${BACKEND}/admin/checklists`, { headers:{Authorization:'Bearer '+t}});
        const data = await res.json();
        // build rows only for filtered keys
        const rows = keys.map(k=>{
          const v = data[k] || {};
          return {
            key: k,
            last_verified: v.last_verified || "",
            fees: v.fees || "",
            processing: v.processing || "",
            items_json: JSON.stringify(v.items || []),
            sources_json: JSON.stringify(v.sources || [])
          };
        });
        const csv = toCSV(rows);
        const blob = new Blob([csv], {type:"text/csv;charset=utf-8"});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = "visaready_filtered.csv"; a.click();
        URL.revokeObjectURL(url);
        toast(`Exported ${rows.length} rows`, 'ok');
      }catch(e){ console.error(e); toast('Export failed','err'); }
    };
  }

  // ---------- AUDIT VIEWER CARD ----------
  function auditViewer(){
    const main = document.querySelector('.vr-main') || document.querySelector('main.container'); if(!main) return;
    if (document.getElementById('auditCard')) return;

    const card = document.createElement('section'); card.className='vr-card'; card.id='auditCard';
    card.innerHTML = `
      <h2 class="h2">Audit Viewer</h2>
      <div class="vr-action-pro">
        <div class="vr-field">Start <input id="au_start" class="vr-input-sm" type="number" value="0" min="0" style="width:100px"></div>
        <div class="vr-field">Limit <input id="au_limit" class="vr-input-sm" type="number" value="200" min="1" max="2000" style="width:100px"></div>
        <button id="au_load" class="vr-btn-sm">Load</button>
        <button id="au_copy" class="vr-btn-sm vr-btn-ghost">Copy</button>
      </div>
      <div id="au_list" class="vr-list"></div>
    `;
    main.appendChild(card);

    const t = ()=> token();

    document.getElementById('au_load').onclick = async ()=>{
      try{
        const start = parseInt(document.getElementById('au_start').value||'0',10);
        const limit = parseInt(document.getElementById('au_limit').value||'200',10);
        const r = await fetch(`${BACKEND}/admin/audit/view?start=${start}&limit=${limit}`, { headers:{Authorization:'Bearer '+t()}});
        if(!r.ok){ toast('Load failed','err'); return; }
        const j = await r.json();
        const list = document.getElementById('au_list'); list.innerHTML = '';
        (j.items||[]).forEach(line=>{
          const div=document.createElement('div');
          try{
            const obj = JSON.parse(line);
            div.textContent = `${obj.ts||''} • ${obj.user||'-'} • ${obj.action||'-'} • ${obj.key||''} ${obj.ok?'✔':'✖'} ${obj.reason?'• '+obj.reason:''}`;
          }catch(_){ div.textContent = line; }
          list.appendChild(div);
        });
        toast(`Loaded ${j.items?.length||0}/${j.total||0}`, 'ok');
      }catch(e){ console.error(e); toast('Load failed','err'); }
    };

    document.getElementById('au_copy').onclick = ()=>{
      const txt = Array.from(document.getElementById('au_list').children).map(n=>n.textContent).join('\\n');
      navigator.clipboard.writeText(txt).then(()=>toast('Copied to clipboard','ok'), ()=>toast('Copy failed','err'));
    };
  }

  // ---------- COMMAND PALETTE add-ons ----------
  function extendPalette(){
    if (!window.__vr_cmd_extend) window.__vr_cmd_extend = [];
    // Create Scoped Admin (if endpoint exists)
    window.__vr_cmd_extend.push({k:'Admin: Create scoped user', a: ()=> openCreateScopedUser() });
    // Flag Outdated Now (uses existing bulk refresh button if present)
    window.__vr_cmd_extend.push({k:'Admin: Flag outdated (last_verified=today for filtered)', a: ()=>{
      const btn = document.getElementById('ks_bulk_today');
      if(btn) btn.click(); else toast('Bulk refresh tool not found','warn');
    }});
    // Merge into existing palette if Batch1 is present
    const hook = window.commandPalette;
    if (hook) { try{ hook(); }catch(_){ } }
  }

  function openCreateScopedUser(){
    const modal = document.createElement('div');
    modal.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;z-index:9999';
    modal.innerHTML = `
      <div style="width:92%;max-width:560px;background:rgba(17,25,40,.95);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px">
        <h3 style="margin:0 0 8px 0">Create Scoped Admin</h3>
        <div class="vr-row"><div class="vr-field">Email <input id="ua_email" class="vr-input-sm" placeholder="admin@example.com"></div></div>
        <div class="vr-row"><div class="vr-field">Master Password <input id="ua_master" type="password" class="vr-input-sm" placeholder="ADMIN_PASSWORD env"></div></div>
        <div class="vr-row">
          <div class="vr-field">Read-only <input id="ua_ro" type="checkbox"></div>
          <div class="vr-field">Countries (CSV) <input id="ua_countries" class="vr-input-sm" placeholder="e.g. IN,GB,DE"></div>
          <div class="vr-field">Visa types (CSV) <input id="ua_visas" class="vr-input-sm" placeholder="e.g. STUDENT,WORK"></div>
        </div>
        <div class="vr-row"><div class="vr-field">Expires YYYY-MM-DD <input id="ua_exp" class="vr-input-sm" placeholder=""></div></div>
        <div class="vr-row" style="margin-top:10px">
          <button id="ua_create" class="vr-btn-sm">Create</button>
          <button id="ua_close" class="vr-btn-sm vr-btn-ghost">Close</button>
          <div id="ua_msg" class="vr-badge-green" style="display:none"></div>
        </div>
      </div>`;
    document.body.appendChild(modal);
    modal.querySelector('#ua_close').onclick = ()=> modal.remove();
    modal.querySelector('#ua_create').onclick = async ()=>{
      try{
        const email = document.getElementById('ua_email').value.trim();
        const master = document.getElementById('ua_master').value;
        const ro = document.getElementById('ua_ro').checked;
        const countries = (document.getElementById('ua_countries').value||'').split(',').map(x=>x.trim()).filter(Boolean);
        const visas = (document.getElementById('ua_visas').value||'').split(',').map(x=>x.trim()).filter(Boolean);
        const exp = document.getElementById('ua_exp').value.trim();
        if(!email || !master){ toast('Email and Master password required','warn'); return; }
        const res = await fetch(`${BACKEND}/admin/users`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ master_password: master, username: email, read_only: ro, regions: countries, visa_types: visas, expires_at: exp })
        });
        if(!res.ok){ toast('Create failed: '+(await res.text()), 'err'); return; }
        modal.querySelector('#ua_msg').style.display='block';
        modal.querySelector('#ua_msg').textContent='Created ✔';
      }catch(e){ console.error(e); toast('Create failed','err'); }
    };
  }

  // ---------- bootstrap ----------
  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      inlineTemplates();
      csvExportFiltered();
      auditViewer();
      roleAware();
      extendPalette();
    }catch(e){ console.error('Batch23 UI error', e); }
  });

})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Batch 2+3 UI injected. Reload /admin (Ctrl+F5).")
