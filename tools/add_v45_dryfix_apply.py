import os, re

ADMIN_HTML = os.path.join("frontend","admin","index.html")

def ensure_backend_const(html: str) -> str:
    if "const BACKEND" not in html:
        html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)
    return html

def insert_button(html: str) -> str:
    # Insert the new button alongside the existing ones in the Validate card
    if 'id="val_dry_apply_btn"' in html:
        return html
    # Find the Validate card button row (near val_btn / val_fix_btn / val_msg)
    html = html.replace(
        'id="val_fix_btn"',
        'id="val_fix_btn" style="margin-left:8px;">Fix trivial issues</button>\n    <button class="btn" id="val_dry_btn" style="margin-left:8px;">Dry-run Fix</button>\n    <button class="btn" id="val_dry_apply_btn" style="margin-left:8px;">Dry-run + Apply</button'
    )
    return html

def insert_js(html: str) -> str:
    if "function downloadTextFile(" not in html:
        html = html.replace("</body>", """
<script>
function downloadTextFile(filename, text){
  const blob = new Blob([text], {type:'text/plain;charset=utf-8;'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
</script>
</body>""")

    # Wire the new Dry-run + Apply handler
    if "document.getElementById('val_dry_apply_btn')" not in html:
        html = html.replace("</body>", """
<script>
(async function wireDryRunApply(){
  const btn = document.getElementById('val_dry_apply_btn');
  if(!btn) return;

  async function ensureLogin(){
    if(window.VAL_TOKEN) return;
    if (typeof val_login === 'function') {
      await val_login();
      return;
    }
    const pwdEl = document.getElementById('val_pwd');
    const pwd = pwdEl ? pwdEl.value.trim() : '';
    const res = await fetch(`${BACKEND}/admin/login`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ password: pwd })
    });
    if(!res.ok) throw new Error('Login failed');
    window.VAL_TOKEN = (await res.json()).token;
  }

  btn.onclick = async () => {
    const msg = document.getElementById('val_msg');
    const out = document.getElementById('val_out');
    msg.textContent = ''; out.textContent = '';

    try{
      await ensureLogin();

      // 1) Dry-run
      const r1 = await fetch(`${BACKEND}/admin/validate/dryfix`, {
        method:'POST', headers:{'Authorization':'Bearer '+window.VAL_TOKEN}
      });
      if(!r1.ok){ msg.textContent = 'Dry-run failed: ' + (await r1.text()); return; }
      const d1 = await r1.json();

      const changes = Array.isArray(d1.changes) ? d1.changes : [];
      msg.textContent = `Dry-run — Fixed: ${d1.fixed}, Normalized: ${d1.normalized}, Changes: ${changes.length}`;
      if(changes.length === 0){
        out.textContent = 'No changes needed.';
        return;
      }
      out.textContent = changes.map(c => `• ${c.key} — ${c.path}: ${JSON.stringify(c.old)} → ${JSON.stringify(c.new)}`).join('\\n');

      // Offer diff download
      if(!document.getElementById('val_dry_dl')){
        const dl = document.createElement('button');
        dl.id='val_dry_dl'; dl.className='btn'; dl.style.marginLeft='8px'; dl.textContent='Download diff';
        dl.onclick=()=>downloadTextFile('visaready_dryfix_diff.txt', out.textContent);
        document.getElementById('val_btn').parentNode.appendChild(dl);
      }

      // 2) Confirm and apply
      const ok = window.confirm('Apply these fixes now?');
      if(!ok) return;

      const r2 = await fetch(`${BACKEND}/admin/validate/fix`, {
        method:'POST', headers:{'Authorization':'Bearer '+window.VAL_TOKEN}
      });
      if(!r2.ok){ msg.textContent = 'Fix failed: ' + (await r2.text()); return; }
      const d2 = await r2.json();
      msg.textContent = `Applied ✔ Fixed: ${d2.fixed}, Normalized: ${d2.normalized}. Re-validating…`;

      // 3) Re-run validation
      const r3 = await fetch(`${BACKEND}/admin/validate`, {
        headers:{'Authorization':'Bearer '+window.VAL_TOKEN}
      });
      if(!r3.ok){ msg.textContent += '  (Validation fetch failed)'; return; }
      const d3 = await r3.json();
      msg.textContent += `  Issues now: ${d3.count}`;
      out.textContent = d3.count === 0 ? 'All good ✔'
        : (d3.issues||[]).map(i=>`• ${i.key} — ${i.issue}`).join('\\n');

    }catch(e){
      console.error(e);
      msg.textContent = 'Dry-run + Apply failed (see console).';
    }
  };
})();
</script>
</body>""")

    # Ensure BACKEND const exists
    html = ensure_backend_const(html)
    return html

def main():
    if not os.path.exists(ADMIN_HTML):
        print(f"Not found: {ADMIN_HTML}")
        return
    html = open(ADMIN_HTML, "r", encoding="utf-8").read()
    orig = html
    html = insert_button(html)
    html = insert_js(html)
    if html != orig:
        open(ADMIN_HTML, "w", encoding="utf-8").write(html)
        print("v4.5 Dry-run + Apply added to Admin.")
    else:
        print("No changes (button/handler already present).")

if __name__ == "__main__":
    main()
