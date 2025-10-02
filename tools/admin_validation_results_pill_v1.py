import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-val-pill */" in html:
    print("Validation results pill already injected.")
    sys.exit(0)

# Ensure BACKEND const exists (no-op if it’s already defined earlier)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-val-pill -->
<style>
/* Validation Results Pill */
.vr-pill { display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px;
  border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.06); color:#dbeafe; font-weight:700; }
.vr-pill.ok  { background:rgba(16,185,129,.12); border-color:rgba(16,185,129,.45); color:#bbf7d0; }
.vr-pill.warn{ background:rgba(245,158,11,.12); border-color:rgba(245,158,11,.45); color:#fde68a; }
</style>

<script>
/* v-admin-val-pill */
(function(){
  function ensurePill(){
    const sec = document.getElementById('validateCard'); if(!sec) return null;
    const bar = sec.querySelector('.vr-actionbar') || sec;
    let pill = document.getElementById('vr_val_pill');
    if (!pill){
      pill = document.createElement('span');
      pill.id = 'vr_val_pill';
      pill.className = 'vr-pill';
      pill.textContent = 'Issues: —';
      pill.style.marginLeft = '8px';
      bar.appendChild(pill);
    }
    return pill;
  }

  // Parse current results from the Validation output panel
  function computeIssues(){
    const out = document.getElementById('val_out');
    if(!out) return null;
    const txt = (out.textContent || '').trim();

    // Cases:
    // - "All good ✔" → 0
    // - List of lines like "• key — issue" → count bullets
    // - Otherwise, try to count lines that look like issues
    if (/All good/i.test(txt)) return 0;

    const lines = txt.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const bullets = lines.filter(l => l.startsWith('• '));
    if (bullets.length) return bullets.length;

    // fallback: look for "Issues found: N"
    const m = txt.match(/Issues?\s*found:\s*(\d+)/i);
    if (m) return parseInt(m[1], 10);

    // unknown
    return null;
  }

  function updatePill(){
    const pill = ensurePill(); if(!pill) return;
    const n = computeIssues();

    pill.className = 'vr-pill'; // reset
    if (n === null){
      pill.textContent = 'Issues: —';
      return;
    }
    if (n === 0){
      pill.textContent = 'Issues: 0';
      pill.classList.add('ok');
    } else {
      pill.textContent = 'Issues: ' + n;
      pill.classList.add('warn');
    }
  }

  // Observe #val_out for changes and update pill automatically
  function observeOut(){
    const out = document.getElementById('val_out');
    if(!out) return;
    const mo = new MutationObserver(()=> updatePill());
    mo.observe(out, { childList:true, subtree:true, characterData:true });
    // initial render
    updatePill();
  }

  // Also hook the buttons (Run / Dry-run / Fix) to trigger pill refresh after a short delay
  function wireButtons(){
    [['val_btn', 550], ['val_dry_btn', 800], ['val_fix_btn', 800]].forEach(([id, delay])=>{
      const el = document.getElementById(id);
      if(!el) return;
      const old = el.onclick;
      el.onclick = (e)=>{
        if(old) old.call(el, e);
        setTimeout(updatePill, delay);
      };
    });
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      ensurePill();
      observeOut();
      wireButtons();
      // Also try periodic refresh in case the panel is updated indirectly
      setInterval(updatePill, 1500);
    }catch(e){ console.error('val pill inject error', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Validation results pill injected. Reload /admin (Ctrl+F5).")
