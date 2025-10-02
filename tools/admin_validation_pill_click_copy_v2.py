import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found"); sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-val-pill-click-copy */" in html:
    print("Validation pill click+copy already injected.")
    sys.exit(0)

# Ensure BACKEND const exists somewhere (no-op if already present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-val-pill-click-copy -->
<style>
.vr-pill { cursor:pointer; user-select:none; position:relative; }
.vr-pill .vr-copy {
  width:16px; height:16px; display:inline-block; margin-left:8px; opacity:.85;
  background:linear-gradient(180deg, rgba(255,255,255,.9), rgba(255,255,255,.7));
  -webkit-mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="%23000" viewBox="0 0 24 24"><path d="M16 1H4a2 2 0 0 0-2 2v12h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z"/></svg>') center/contain no-repeat;
          mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="%23000" viewBox="0 0 24 24"><path d="M16 1H4a2 2 0 0 0-2 2v12h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z"/></svg>') center/contain no-repeat;
  transition:opacity .15s ease;
}
.vr-pill:hover .vr-copy{ opacity:1; }
</style>

<script>
/* v-admin-val-pill-click-copy */
(function(){
  function pill(){ return document.getElementById('vr_val_pill'); }
  function out(){  return document.getElementById('val_out'); }

  function copyIssuesText(){
    const panel = out();
    const txt = (panel?.textContent || '').trim();
    const bullets = txt || 'No issues.';
    navigator.clipboard.writeText(bullets)
      .then(()=> toast('Issues copied', 'ok', 1200))
      .catch(()=> toast('Copy failed', 'err', 1600));
  }

  function ensureClickAndCopy(){
    const p = pill(); if(!p) return;

    // Make entire pill scroll to results
    if (!p.__vr_click_bound){
      p.addEventListener('click', (e)=>{
        // If click landed on copy button, let the copy handler do its job
        if (e.target && e.target.classList && e.target.classList.contains('vr-copy')) return;
        const panel = out();
        if(panel){
          panel.scrollIntoView({ behavior:'smooth', block:'start' });
          toast('Jumped to results','ok', 1000);
        }
      });
      p.__vr_click_bound = true;
    }

    // Append copy icon once
    if (!p.querySelector('.vr-copy')){
      const c = document.createElement('span');
      c.className = 'vr-copy';
      c.title = 'Copy issues';
      c.style.verticalAlign = 'middle';
      c.style.display = 'inline-block';
      c.style.cursor = 'pointer';
      c.addEventListener('click', (e)=>{ e.stopPropagation(); copyIssuesText(); });
      p.appendChild(c);
    }
  }

  // Reuse global toast if available, else a minimal fallback
  function toast(msg, kind='ok', ms=1500){
    let box = document.getElementById('vr_toast');
    if(!box){
      box = document.createElement('div');
      box.id='vr_toast';
      box.style.cssText='position:fixed;right:16px;bottom:16px;z-index:9999;padding:10px 12px;border-radius:10px;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.45);color:#d1fae5;display:none';
      document.body.appendChild(box);
    }
    box.textContent = msg; box.style.display='block';
    clearTimeout(window.__vr_toast_t); window.__vr_toast_t=setTimeout(()=>{box.style.display='none'}, ms);
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      // initial render
      setTimeout(ensureClickAndCopy, 200);
      // also re-ensure after any known actions
      ['val_btn','val_dry_btn','val_fix_btn'].forEach(id=>{
        const el = document.getElementById(id);
        if(!el) return;
        const old = el.onclick;
        el.onclick = (e)=>{ if(old) old.call(el,e); setTimeout(ensureClickAndCopy, 500); };
      });
      // periodic fallback
      setInterval(ensureClickAndCopy, 1500);
    }catch(e){ console.error('val-pill click/copy inject error', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Validation pill click+copy injected. Reload /admin (Ctrl+F5).")
