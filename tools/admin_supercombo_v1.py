import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-supercombo */" in html:
    print("Super Combo already injected.")
    sys.exit(0)

# Ensure BACKEND const exists somewhere (no-op if already present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-supercombo -->
<script>
/* v-admin-supercombo */
(function(){
  // ---------- helpers ----------
  function getToken(){ return window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || ''; }
  function reasonHeader(){
    const r = (document.getElementById('vr_reason')||{}).value || '';
    return r ? {'X-Reason': r} : {};
  }
  function toast(msg, kind='ok', ms=2400){
    let box = document.getElementById('vr_toast'); if(!box){ box=document.createElement('div'); box.id='vr_toast'; document.body.appendChild(box); }
    box.className='vr-toast '+(kind==='err'?'err':(kind==='warn'?'warn':'ok'));
    box.textContent = msg; box.style.display='block';
    clearTimeout(window.__vr_toast_t); window.__vr_toast_t=setTimeout(()=>{box.style.display='none'}, ms);
  }
  function click(id){ const el=document.getElementById(id); if(!el) throw new Error('Missing '+id); el.click(); }
  function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

  // ---------- HUD (reuse if exists from Action Bar Pro) ----------
  function ensureHUD(){
    let HUD = document.querySelector('.vr-hud');
    if (HUD) return { HUD, set: setStepExisting };
    // lightweight fallback HUD
    HUD = document.createElement('div'); HUD.className='vr-hud'; HUD.style.display='none';
    HUD.innerHTML = `
      <div class="vr-hud-card">
        <h3 id="vr_hud_title_sc" style="margin:0 0 10px 0">Super Combo</h3>
        <div class="vr-steps">
          <div class="vr-step"><div id="sc_dot_1" class="vr-dot"></div><div id="sc_txt_1">Save</div></div>
          <div class="vr-step"><div id="sc_dot_2" class="vr-dot"></div><div id="sc_txt_2">Dry-run</div></div>
          <div class="vr-step"><div id="sc_dot_3" class="vr-dot"></div><div id="sc_txt_3">Fix & Validate</div></div>
        </div>
        <div class="vr-hud-actions"><button id="sc_close" class="vr-btn-mini vr-btn-ghost">Close</button></div>
      </div>`;
    document.body.appendChild(HUD);
    document.getElementById('sc_close').onclick = ()=> HUD.style.display='none';
    function setStepFallback(n, state, text){
      const dot = document.getElementById('sc_dot_'+n);
      const txt = document.getElementById('sc_txt_'+n);
      if(dot) dot.className = 'vr-dot ' + (state==='run'?'run':state==='ok'?'ok':state==='err'?'err':'');
      if(txt && text) txt.textContent = text;
    }
    return { HUD, set: setStepFallback };
    function setStepExisting(n, state, text){
      const dot = document.getElementById(n===1?'vr_dot_1':n===2?'vr_dot_2':'vr_dot_3');
      const txt = document.getElementById(n===1?'vr_txt_1':n===2?'vr_txt_2':'vr_txt_3');
      if(dot) dot.className = 'vr-dot ' + (state==='run'?'run':state==='ok'?'ok':state==='err'?'err':'');
      if(txt && text) txt.textContent = text;
    }
  }

  // ---------- inject button ----------
  function injectButton(){
    const sec = document.getElementById('validateCard'); if(!sec) return;
    if (document.getElementById('vr_super_combo')) return;

    const bar = sec.querySelector('.vr-actionbar') || sec;
    const btn = document.createElement('button');
    btn.id = 'vr_super_combo';
    btn.className = 'vr-ab-btn';
    btn.textContent = 'Super Combo: Save → Dry-run → Fix → Validate';
    btn.style.marginLeft = '8px';
    bar.appendChild(btn);

    btn.onclick = runSuperCombo;
  }

  // ---------- run super combo ----------
  async function runSuperCombo(){
    const {HUD, set} = ensureHUD();
    HUD.style.display='flex';

    try{
      // Step 1: Save
      set(1,'run','Saving…');
      try {
        click('ie_saveBtn');
      } catch(e) {
        // inline editor may not be used; treat as optional
      }
      await sleep(500);
      set(1,'ok','Saved ✔');

      // Step 2: Dry-run (get change count)
      set(2,'run','Dry-run…');
      const t = getToken();
      if(!t){ throw new Error('No token'); }
      const r = await fetch(`${BACKEND}/admin/validate/dryfix`, {
        method:'POST',
        headers: Object.assign({'Authorization':'Bearer '+t,'Content-Type':'application/json'}, reasonHeader())
      });
      if(!r.ok){
        set(2,'err','Dry-run failed'); toast('Dry-run failed','err'); return;
      }
      const j = await r.json();
      const changes = Array.isArray(j.changes) ? j.changes.length : 0;
      set(2,'ok',`Dry-run: ${changes} changes`);
      await sleep(300);

      // Confirm if there are changes to fix
      if (changes > 0){
        const ok = window.confirm(`Dry-run found ${changes} change(s).\n\nApply Fix now and then Validate?`);
        if(!ok){
          set(3,'err','Cancelled by user'); toast('Cancelled','warn'); return;
        }
      }

      // Step 3: Fix → Validate
      set(3,'run','Fix…');
      const fixBtn = document.getElementById('val_fix_btn');
      if (fixBtn) { fixBtn.click(); await sleep(600); set(3,'run','Validate…'); }
      const valBtn = document.getElementById('val_btn');
      if (valBtn) { valBtn.click(); await sleep(400); }
      set(3,'ok','Done ✔');
      toast('Super Combo initiated','ok');
    }catch(e){
      console.error(e);
      set(1,'err'); set(2,'err'); set(3,'err');
      toast('Super Combo failed','err');
    }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{ injectButton(); }catch(e){ console.error('super combo', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Super Combo injected. Reload /admin (Ctrl+F5).")
