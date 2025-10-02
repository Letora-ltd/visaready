import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found"); sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

if "/* v-admin-batch1 */" in html:
    print("Batch 1 already applied."); sys.exit(0)

inject = r"""
<!-- v-admin-batch1 -->
<style>
/* ===== Batch1 ===== */
.vr-actionbar{position:sticky; top:68px; z-index:50; display:flex; gap:8px; align-items:center;
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.08); border-radius:12px; padding:8px 10px; margin:-8px -8px 12px -8px;}
.vr-ab-title{font-weight:800; letter-spacing:.2px; color:#cbd5e1; margin-right:10px}
.vr-ab-btn{padding:8px 10px;border:none;border-radius:10px;font-weight:700;cursor:pointer;background:#A3E635;color:#07121f; box-shadow:0 8px 22px rgba(163,230,53,.3)}
.vr-ab-btn.alt{background:#60a5fa; box-shadow:0 8px 22px rgba(96,165,250,.3)}
.vr-ab-btn.warn{background:#f59e0b; box-shadow:0 8px 22px rgba(245,158,11,.3)}
.vr-ab-btn.ghost{background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.12); color:#dbeafe}
.vr-help{cursor:pointer; font-weight:800; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); width:26px; height:26px; display:grid; place-items:center; border-radius:8px; color:#dbeafe}
.vr-tip{position:absolute; background:rgba(8,12,22,.96); border:1px solid rgba(255,255,255,.08); color:#cbd5e1; padding:10px 12px; border-radius:12px; width:max-content; max-width:420px; box-shadow:0 14px 34px rgba(0,0,0,.45); display:none}
.vr-toast{position:fixed; right:16px; bottom:16px; min-width:240px; padding:12px 14px; border-radius:12px; display:none; z-index:9999}
.vr-toast.ok{background:rgba(16,185,129,.12); border:1px solid rgba(16,185,129,.45); color:#d1fae5}
.vr-toast.warn{background:rgba(245,158,11,.12); border:1px solid rgba(245,158,11,.45); color:#fde68a}
.vr-toast.err{background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.45); color:#fecaca}
.vr-density-toggle{margin-left:auto; display:flex; align-items:center; gap:8px}
.compact .vr-card{padding:12px}
.compact table td, .compact table th{padding:6px 6px !important; font-size:13px}
</style>

<script>
/* v-admin-batch1 */
(function(){
  // ---------- Toast ----------
  function toast(msg, kind='ok', ms=2400){
    let box = document.getElementById('vr_toast'); if(!box){
      box=document.createElement('div'); box.id='vr_toast'; document.body.appendChild(box);
    }
    box.className='vr-toast '+kind; box.textContent=msg; box.style.display='block';
    clearTimeout(window.__vr_toast_t); window.__vr_toast_t=setTimeout(()=>{box.style.display='none'}, ms);
  }

  // ---------- Help tips ----------
  function tip(el, text){
    let t = document.createElement('div'); t.className='vr-tip'; t.textContent = text; document.body.appendChild(t);
    const rect = el.getBoundingClientRect(); t.style.left = (rect.left+window.scrollX)+'px'; t.style.top = (rect.bottom+8+window.scrollY)+'px';
    t.style.display='block'; function close(){ t.remove(); document.body.removeEventListener('click', close); }
    setTimeout(()=>document.body.addEventListener('click', close), 0);
  }

  // ---------- Density toggle ----------
  function densityToggle(){
    const shell = document.body; const chk = document.getElementById('vr_dense_chk');
    if(chk && chk.checked){ shell.classList.add('compact'); } else { shell.classList.remove('compact'); }
  }

  // ---------- Action Bars ----------
  function insertActionBar(sectionId, title, buttons){
    const sec = document.getElementById(sectionId); if(!sec) return;
    if (sec.querySelector('.vr-actionbar')) return;
    const wrap = document.createElement('div'); wrap.className='vr-actionbar';
    const ttl = document.createElement('div'); ttl.className='vr-ab-title'; ttl.textContent = title;
    wrap.appendChild(ttl);
    buttons.forEach(b=>{
      const btn=document.createElement('button'); btn.className='vr-ab-btn '+(b.kind||''); btn.textContent=b.label;
      btn.onclick=b.onClick; wrap.appendChild(btn);
    });
    const help = document.createElement('div'); help.className='vr-help'; help.textContent='?';
    help.title='help'; help.onclick = ()=> tip(help, (sec.getAttribute('data-help')||'No help provided.'));
    wrap.appendChild(help);

    // density
    const dens = document.createElement('label'); dens.className='vr-density-toggle';
    dens.innerHTML = `<span class="small" style="color:#cbd5e1">Compact</span><input id="vr_dense_chk" type="checkbox" />`;
    wrap.appendChild(dens);
    sec.prepend(wrap);
    const chk = document.getElementById('vr_dense_chk'); chk.onchange = densityToggle;
  }

  // Wrap existing actions
  function wireAll(){
    // Inline Editor
    insertActionBar('inlineEditor','Inline Editor',[
      {label:'Load', onClick: ()=>{ const el=document.getElementById('ie_loadBtn'); if(el) el.click(); }, kind:'ghost'},
      {label:'Save', onClick: ()=>{ const el=document.getElementById('ie_saveBtn'); if(el) el.click(); }},
    ]);
    document.getElementById('inlineEditor')?.setAttribute('data-help','Format: Title :: Details :: URL (optional). Save writes to checklists.json.');

    // Duplicate
    insertActionBar('dupCard','Duplicate',[
      {label:'Duplicate', onClick: ()=>{ document.getElementById('dup_btn')?.click(); }},
    ]);
    document.getElementById('dupCard')?.setAttribute('data-help','Copy one corridor to another. Use Overwrite to replace existing.');

    // Bulk Duplicate
    insertActionBar('bulkDupCard','Bulk Duplicate',[
      {label:'Duplicate', onClick: ()=>{ document.getElementById('bdup_btn')?.click(); }},
    ]);
    document.getElementById('bulkDupCard')?.setAttribute('data-help','Paste multiple destination keys (one per line).');

    // Validation
    insertActionBar('validateCard','Validation',[
      {label:'Run', onClick: ()=>{ document.getElementById('val_btn')?.click(); }, kind:'ghost'},
      {label:'Dry-run', onClick: ()=>{ document.getElementById('val_dry_btn')?.click(); }, kind:'alt'},
      {label:'Fix', onClick: ()=>{ document.getElementById('val_fix_btn')?.click(); }, kind:'warn'},
    ]);
    document.getElementById('validateCard')?.setAttribute('data-help','Dry-run shows proposed changes; Fix applies trivial changes. Add Reason to be audited.');

    // Toast hooks: wire common actions to show feedback
    const map = [
      ['ie_saveBtn','Saved ✔','ok'], ['dup_btn','Duplicate requested','ok'], ['bdup_btn','Bulk requested','ok'],
      ['val_btn','Validation running…','warn'], ['val_fix_btn','Fix requested','warn'], ['val_dry_btn','Dry-run requested','warn']
    ];
    map.forEach(([id,msg,kind])=>{
      const el = document.getElementById(id); if(el){ const old=el.onclick; el.onclick = (e)=>{ try{ toast(msg,kind); }catch(_){}; if(old) old.call(el,e); };
    });
  }

  // ---------- Command Palette (Ctrl + K) ----------
  function commandPalette(){
    let open=false, box=null, input=null, list=null;
    const cmds = [
      {k:'Go: Search & Filters', a:()=>location.hash='#keySearchCard'},
      {k:'Go: Inline Editor', a:()=>location.hash='#inlineEditor'},
      {k:'Go: Duplicate', a:()=>location.hash='#dupCard'},
      {k:'Go: Bulk Duplicate', a:()=>location.hash='#bulkDupCard'},
      {k:'Go: Validation', a:()=>location.hash='#validateCard'},
      {k:'Open CSV', a:()=>location.href='./csv.html'},
      {k:'Run: Validation', a:()=>document.getElementById('val_btn')?.click()},
      {k:'Run: Dry-run', a:()=>document.getElementById('val_dry_btn')?.click()},
      {k:'Run: Fix', a:()=>document.getElementById('val_fix_btn')?.click()},
      {k:'Save: Inline Editor', a:()=>document.getElementById('ie_saveBtn')?.click()},
    ];
    function build(){
      box=document.createElement('div');
      box.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;z-index:9999;align-items:center;justify-content:center';
      box.innerHTML = `
        <div style="width:92%;max-width:640px;background:rgba(17,25,40,.95);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:14px">
          <input id="vr_k_input" class="vr-input" placeholder="Type a command (e.g., Go: Inline, Run: Validation)" style="width:100%;padding:12px 14px">
          <div id="vr_k_list" style="margin-top:12px;max-height:320px;overflow:auto"></div>
        </div>`;
      document.body.appendChild(box);
      input=box.querySelector('#vr_k_input'); list=box.querySelector('#vr_k_list');
      input.oninput = render; render();
      box.addEventListener('click', e=>{ if(e.target===box) hide(); })
      input.addEventListener('keydown', e=>{ if(e.key==='Escape') hide(); if(e.key==='Enter'){ const first=list.querySelector('button'); if(first) first.click(); }});
    }
    function render(){
      const q=(input.value||'').toLowerCase().trim();
      list.innerHTML='';
      cmds.filter(c=>!q || c.k.toLowerCase().includes(q)).forEach(c=>{
        const b=document.createElement('button'); b.className='vr-ab-btn ghost'; b.style.width='100%'; b.style.textAlign='left'; b.textContent=c.k;
        b.onclick=()=>{ c.a(); hide(); toast(c.k, 'ok', 1200); };
        list.appendChild(b);
      });
    }
    function show(){ if(!box) build(); box.style.display='flex'; input.focus(); input.select(); open=true; }
    function hide(){ if(!box) return; box.style.display='none'; open=false; }
    window.addEventListener('keydown', e=>{ if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='k'){ e.preventDefault(); open?hide():show(); } });
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{ wireAll(); commandPalette(); toast('Productivity tools ready', 'ok', 1600); }catch(e){ console.error(e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Batch 1 injected. Reload /admin (Ctrl+F5).")
