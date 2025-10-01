import os, re

INDEX = os.path.join("frontend","index.html")

html = open(INDEX, "r", encoding="utf-8").read()

# Add button near fees/processing card if not present
if 'id="pdfBtn"' not in html:
    html = html.replace(
        '<div id="ptime" class="small" style="margin-top:6px;"></div>\n        </div>\n      </section>',
        '<div id="ptime" class="small" style="margin-top:6px;"></div>\n          <div style="margin-top:10px;"><button class="btn" id="pdfBtn">Download PDF</button></div>\n        </div>\n      </section>'
    )

# Add printer window builder
if "function buildPdfWindow(" not in html:
    html = html.replace("</script>\n  </body>", """
  function buildPdfWindow(title, verified, items, fees, ptime, sources){
    const w = window.open('', '_blank');
    const css = `
      body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:24px;color:#0f172a;}
      h1{margin:0 0 4px 0;font-size:20px} .small{color:#64748b;font-size:12px}
      .item{margin:10px 0} .src{font-size:12px;margin-top:6px}
      .badge{display:inline-block;background:#ecfdf5;color:#065f46;padding:4px 8px;border-radius:999px;font-size:12px}
      hr{border:none;height:1px;background:#e2e8f0;margin:16px 0}
    `;
    const html = `
      <html><head><title>${title}</title><style>${css}</style></head><body>
      <h1>${title}</h1>
      <div class="small"><span class="badge">Last verified: ${verified||'—'}</span></div>
      <hr/>
      <h2>Checklist</h2>
      ${items.map((it,i)=>`<div class="item"><strong>${i+1}. ${it.title||''}</strong><div class="small">${it.details||''}</div></div>`).join('')}
      <hr/>
      <h2>Fees & Processing</h2>
      <div>${fees||''}</div>
      <div class="small">${ptime||''}</div>
      ${Array.isArray(sources)&&sources.length?`<hr/><h2>Official Sources</h2><ul class="small">${sources.map(s=>`<li><a href="${s.url||'#'}" target="_blank">${s.label||s.url||''}</a></li>`).join('')}</ul>`:''}
      </body></html>`;
    w.document.open(); w.document.write(html); w.document.close();
    setTimeout(()=>w.print(), 300);
  }
""" + "\n</script>\n  </body>")

# Wire up to existing data (reuse variables defined in main script)
html = re.sub(
    r"results\.style\.display = \"block\";[\s\S]*?};\s*\}\);",
    r"""results.style.display = "block";
          window.scrollTo({ top: results.offsetTop - 12, behavior: 'smooth' });
          const pdfBtn = document.getElementById('pdfBtn');
          if(pdfBtn){
            pdfBtn.onclick = ()=> buildPdfWindow(title.textContent, verifiedDate.textContent, cl.items, cl.fees, cl.processing, cl.sources||[]);
          }
        };
      });""",
    html
)

open(INDEX, "w", encoding="utf-8").write(html)
print("v4.0 PDF preview/download button added to results.")
