import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-session-hotkey-palette */" in html:
    print("Session hotkey + palette already injected.")
    sys.exit(0)

# Ensure BACKEND const exists (no-op if already present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-session-hotkey-palette -->
<script>
/* v-admin-session-hotkey-palette */
(function(){
  // Ensure a Session button/panel exist (from prior patch). If not, create minimal ones.
  function ensureSessionUI(){
    // button in header
    const header = document.querySelector('.vr-header .vr-actions');
    if (header && !document.getElementById('vr_sess_btn')) {
      const b = document.createElement('button');
      b.id='vr_sess_btn'; b.className='vr-btn'; b.textContent='Session';
      b.style.background='#22d3ee'; b.style.boxShadow='0 8px 22px rgba(34,211,238,.35)';
      header.prepend(b);
    }
    // panel
    if (!document.getElementById('vr_sess_pop')) {
      const p = document.createElement('div');
      p.id='vr_sess_pop';
      p.style.cssText='position:fixed;right:18px;top:70px;z-index:120;width:min(92vw,520px);display:none;background:rgba(17,25,40,.95);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:14px;box-shadow:0 20px 60px rgba(0,0,0,.45);color:#dbeafe';
      p.innerHTML = `
        <h3 style="margin:0 0 8px 0">Session details</h3>
        <div id="vr_sess_body_min" class="small" style="opacity:.85">Signed in session info will appear here.</div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">
          <button id="vr_sess_close_min" class="vr-btn" style="background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:#e5f0ff">Close</button>
        </div>`;
      document.body.appendChild(p);
      document.getElementById('vr_sess_close_min').onclick = ()=> p.style.display='none';
    }
  }

  function toggleSession(){
    let btn = document.getElementById('vr_sess_btn');
    let panel = document.getElementById('vr_sess_pop');
    if (!btn || !panel){ ensureSessionUI(); btn = document.getElementById('vr_sess_btn'); panel = document.getElementById('vr_sess_pop'); }
    // If the Session patch with renderPanel() exists, just click the button to run its logic
    if (btn) { try { btn.click(); return; } catch(_){} }
    // Fallback: toggle panel display
    if (panel) panel.style.display = (panel.style.display==='none' || !panel.style.display) ? 'block' : 'none';
  }

  // --- Keyboard shortcut: Ctrl + Shift + S to open Session panel ---
  function wireHotkey(){
    if (window.__vr_sess_hotkey_bound) return;
    window.__vr_sess_hotkey_bound = true;
    window.addEventListener('keydown', (e)=>{
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 's'){
        e.preventDefault();
        toggleSession();
      }
    });
  }

  // --- Command Palette entry: “Session: Show details” ---
  function addPaletteAction(){
    // Batch1/Batch23 register extra actions via window.__vr_cmd_extend
    if (!window.__vr_cmd_extend) window.__vr_cmd_extend = [];
    const exists = window.__vr_cmd_extend.some(x => x && x.k === 'Session: Show details');
    if (!exists) window.__vr_cmd_extend.push({ k:'Session: Show details', a: toggleSession });

    // If a commandPalette builder is present, re-invoke to include the new entries
    if (typeof window.commandPalette === 'function') {
      try { window.commandPalette(); } catch(_) {}
    }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      ensureSessionUI();
      wireHotkey();
      addPaletteAction();
    }catch(e){ console.error('session hotkey/palette inject error', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Session hotkey (Ctrl+Shift+S) + palette action injected. Reload /admin (Ctrl+F5).")
