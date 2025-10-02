import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-palette-hotkeys */" in html:
    print("Palette hotkeys already injected.")
    sys.exit(0)

# Ensure BACKEND const (no-op if already present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-palette-hotkeys -->
<script>
/* v-admin-palette-hotkeys */
(function(){
  // ----- helper: open palette (like Ctrl+K) then prefill query -----
  function openPaletteWith(q){
    // Trigger the palette open (same as Ctrl+K used in Batch 1)
    const ke = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
    window.dispatchEvent(ke);
    // after palette renders, fill the input
    setTimeout(()=>{
      const inp = document.getElementById('vr_k_input');
      if(!inp){
        // If no palette exists, gracefully navigate by hash for common sections
        const map = { validate:'#validateCard', duplicate:'#dupCard', bulk:'#bulkDupCard', csv:'./csv.html', inline:'#inlineEditor' };
        if (q in map) {
          if (map[q].startsWith('#')) location.hash = map[q];
          else location.href = map[q];
        }
        return;
      }
      inp.value = q;
      inp.dispatchEvent(new Event('input', {bubbles:true}));
      inp.focus(); inp.select();
    }, 80);
  }

  // ----- hotkeys → prefill palette -----
  const binds = [
    ['v', 'validate'],
    ['d', 'duplicate'],
    ['b', 'bulk'],
    ['c', 'csv'],
    ['i', 'inline'],
  ];
  if (!window.__vr_palette_hotkeys_bound){
    window.__vr_palette_hotkeys_bound = true;
    window.addEventListener('keydown', (e)=>{
      if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return;
      const k = e.key.toLowerCase();
      const pair = binds.find(([key])=> key===k);
      if(!pair) return;
      e.preventDefault();
      openPaletteWith(pair[1]);
    }, true);
  }

  // ----- add extra palette actions if missing -----
  if (!window.__vr_cmd_extend) window.__vr_cmd_extend = [];
  const reg = window.__vr_cmd_extend;
  const add = (k, a) => { if (!reg.some(x => x && x.k===k)) reg.push({k, a}); };

  // navigation
  add('Go: Search & Filters', ()=> location.hash='#keySearchCard');
  add('Go: Inline Editor',  ()=> location.hash='#inlineEditor');
  add('Go: Duplicate',      ()=> location.hash='#dupCard');
  add('Go: Bulk Duplicate', ()=> location.hash='#bulkDupCard');
  add('Go: Validation',     ()=> location.hash='#validateCard');
  add('Open CSV',           ()=> location.href='./csv.html');

  // actions
  const click = id => { const el = document.getElementById(id); if (el) el.click(); };
  add('Run: Validation',    ()=> click('val_btn'));
  add('Run: Dry-run',       ()=> click('val_dry_btn'));
  add('Run: Fix',           ()=> click('val_fix_btn'));
  add('Save: Inline Editor',()=> click('ie_saveBtn'));

  // If a palette builder exists (from Batch 1), refresh it to include these items
  if (typeof window.commandPalette === 'function') {
    try { window.commandPalette(); } catch(_){}
  }
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Palette hotkeys injected. Reload /admin (Ctrl+F5).")
