import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-actionbar-pro */" in html:
    print("Action Bar Pro already injected.")
    sys.exit(0)

# Ensure BACKEND const is defined somewhere (no-op if already present earlier)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-actionbar-pro -->
<style>
/* progress HUD */
.vr-hud{
  position:fixed; inset:0; display:none; z-index:9999;
  align-items:center; justify-content:center; background:rgba(0,0,0,.45);
}
.vr-hud-card{
  width:92%; max-width:580px; background:rgba(17,25,40,.95);
  border:1px solid rgba(255,255,255,.08); border-radius:16px; padding:18px;
  color:#dbeafe; box-shadow:0 20px 60px rgba(0,0,0,.45)
}
.vr-steps{ display:grid; gap:8px; margin-top:8px }
.vr-step{ display:flex; align-items:center; gap:10px }
.vr-dot{ width:10px; height:10px; border-radius:999px; background:#64748b }
.vr-dot.ok{ background:#22c55e }
.vr-dot.err{ background:#ef4444 }
.vr-dot.run{ background:linear-gradient(90deg,#38bdf8,#a3e635); animation: vr-pulse 1s ease-in-out infinite alternate }
@keyframes vr-pulse{ from{filter:brightness(.8)} to{filter:brightness(1.35)} }
.vr-hud-actions{ display:flex; gap:8px; justify-content:flex-end; margin-top:12px }
.vr-btn-mini{ padding:8px 10px; border:none; border-radius:10px; font-weight:700; cursor:pointer;
  background:#A3E635; color:#07121f; box-shadow:0 8px 22px rgba(163,230,53,.3) }
.vr-btn-ghost{ background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); color:#e5f0ff }
</style>

<script>
/* v-admin-actionbar-pro */
(function(){
  // ---------- HUD ----------
  let HUD, S1, S2, S3, BTN_CLOSE;
  function ensureHUD(){
    if (HUD) return;
    HUD = document.createElement('div');
    HUD.className = 'vr-hud';
    HUD.innerHTML = `
      <div class="vr-hud-card">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <h3 id="vr_hud_title" style="margin:0">Action</h3>
          <div id="vr_hud_role" class="small" style="opacity:.8"></div>
        </div>
        <div class="vr-steps">
          <div class="vr-step"><div id="vr_dot_1" class="vr-dot"></div><div id="vr_txt_1">Step 1</div></div>
          <div class="vr-step"><div id="vr_dot_2" class="vr-dot"></div><div id="vr_txt_2">Step 2</div></div>
          <div class="vr-step"><div id="vr_dot_3" class="vr-dot"></div><div id="vr_txt_3">Step 3</div></div>
        </div>
        <div class="vr-hud-actions">
          <button id="vr_hud_close" class="vr-btn-mini vr-btn-ghost">Close</button>
        </div>
      </div>`;
    document.body.appendChild(HUD);
    S1 = {dot: HUD.querySelector('#vr_dot_1'), txt: HUD.querySelector('#vr_txt_1')};
    S2 = {dot: HUD.querySelector('#vr_dot_2'), txt: HUD.querySelector('#vr_txt_2')};
    S3 = {dot: HUD.querySelector('#vr_dot_3'), txt: HUD.querySelector('#vr_txt_3')};
    BTN_CLOSE = HUD.querySelector('#vr_hud_close');
    BTN_CLOSE.onclick = ()=> HUD.style.display='none';
  }
  async function headerClaims(){
    try{
      const tok = window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || '';
      if(!tok) return null;
      const r = await fetch(`${BACKEND}/auth/whoami`, { headers:{ Authorization:'Bearer '+tok }});
      if(!r.ok) return null; const j = await r.json(); return j.claims||null;
    }catch(e){ return null; }
  }
  function setStep(s, state, text){
    const X = s===1?S1:s===2?S2:S3;
    if(!X) return;
    X.dot.className = 'vr-dot ' + (state==='run'?'run':state==='ok'?'ok':state==='err'?'err':'');
    if(text) X.txt.textContent = text;
  }
  function showHUD(title){
    ensureHUD(); HUD.style.display='flex';
    document.getElementById('vr_hud_title').textContent = title || 'Action';
    setStep(1, '', 'Step 1'); setStep(2, '', 'Step 2'); setStep(3, '', 'Step 3');
    headerClaims().then(c=>{
      document.getElementById('vr_hud_role').textContent = c ? ((c.sub||'?')+' • '+(c.role||'user')) : '';
    });
  }

  // ---------- helpers ----------
  function clickById(id){ const el=document.getElementById(id); if(el) el.click(); else throw new Error('Missing '+id); }
  function wait(ms){ return new Promise(r=>setTimeout(r,ms)); }
  function toast(msg, kind='ok', ms=2400){
    let box = document.getElementById('vr_toast'); if(!box){ box=document.createElement('div'); box.id='vr_toast'; document.body.appendChild(box); }
    box.className='vr-toast '+(kind==='err'?'err':(kind==='warn'?'warn':'ok'));
    box.textContent = msg; box.style.display='block';
    clearTimeout(window.__vr_toast_t); window.__vr_toast_t=setTimeout(()=>{box.style.display='none'}, ms);
  }

  // ---------- Combo 1: Save → Validate (Inline Editor) ----------
  function injectSaveValidate(){
    const sec = document.getElementById('inlineEditor'); if(!sec) return;
    if (document.getElementById('vr_sv_btn')) return;
    const ab = sec.querySelector('.vr-actionbar') || sec;  // place on existing action bar if present
    const btn = document.createElement('button');
    btn.id = 'vr_sv_btn'; btn.className = 'vr-ab-btn alt'; btn.textContent = 'Save → Validate';
    btn.style.marginLeft = '8px';
    btn.onclick = async ()=>{
      try{
        showHUD('Save → Validate');
        setStep(1,'run','Saving…');
        clickById('ie_saveBtn');
        await wait(400); // brief UI debounce
        setStep(1,'ok','Saved ✔');

        setStep(2,'run','Running validation…');
        clickById('val_btn');
        setStep(2,'ok','Validation queued ✔');

        setStep(3,'run','Finalising…');
        await wait(600);
        setStep(3,'ok','Done ✔');
        toast('Saved and validation started','ok');
      }catch(e){
        setStep(1,'err'); setStep(2,'err'); setStep(3,'err');
        toast('Save→Validate failed','err');
      }
    };
    ab.appendChild(btn);
  }

  // ---------- Combo 2: Dry-run → Fix → Validate (Validation) ----------
  function injectDryFixValidate(){
    const sec = document.getElementById('validateCard'); if(!sec) return;
    if (document.getElementById('vr_dfv_btn')) return;
    const ab = sec.querySelector('.vr-actionbar') || sec;
    const btn = document.createElement('button');
    btn.id = 'vr_dfv_btn'; btn.className = 'vr-ab-btn warn'; btn.textContent = 'Dry-run → Fix → Validate';
    btn.style.marginLeft = '8px';
    btn.onclick = async ()=>{
      try{
        showHUD('Dry-run → Fix → Validate');
        setStep(1,'run','Dry-run…');
        const dry = document.getElementById('val_dry_btn');
        if(!dry){ throw new Error('Missing dry-run'); }
        dry.click();
        await wait(700); // give UI time to fetch and show diff
        setStep(1,'ok','Dry-run done ✔');

        setStep(2,'run','Fixing trivial issues…');
        const fix = document.getElementById('val_fix_btn');
        if(!fix){ throw new Error('Missing fix'); }
        fix.click();
        await wait(700);
        setStep(2,'ok','Fix requested ✔');

        setStep(3,'run','Re-validating…');
        const run = document.getElementById('val_btn');
        if(!run){ throw new Error('Missing validate'); }
        run.click();
        await wait(500);
        setStep(3,'ok','Validation queued ✔');
        toast('Dry-run, Fix, Validate initiated','ok');
      }catch(e){
        setStep(1,'err'); setStep(2,'err'); setStep(3,'err');
        toast('DFV failed','err');
      }
    };
    ab.appendChild(btn);
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      injectSaveValidate();
      injectDryFixValidate();
    }catch(e){ console.error('ActionBar Pro injection error', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Action Bar Pro injected. Reload /admin (Ctrl+F5).")
