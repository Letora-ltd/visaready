import os, re

INDEX = os.path.join("frontend","index.html")
ADMIN = os.path.join("frontend","admin","index.html")

# --- Frontend rendering: add per-item badge if item.source_url exists ---
html = open(INDEX, "r", encoding="utf-8").read()
html = html.replace(
    "row.innerHTML = '<div class=\"num\"' + (i+1) + '</div><div><strong>' + item.title + '</strong><br><span class=\"small\">' + item.details + '</span></div>';",
    "row.innerHTML = '<div class=\"num\">' + (i+1) + '</div><div><strong>' + item.title + '</strong>' + (item.source_url? ' <a class=\"small\" style=\"margin-left:8px;\" href=\"'+item.source_url+'\" target=\"_blank\">source</a>':'') + '<br><span class=\"small\">' + item.details + '</span></div>';"
)
open(INDEX, "w", encoding="utf-8").write(html)

# --- Inline editor parsing: support Title :: Details :: URL ---
adm = open(ADMIN, "r", encoding="utf-8").read()
adm = adm.replace(
    "function ie_parseItemsText(text) {",
    """function ie_parseItemsText(text) {
  // supports: Title :: Details  (and optional third :: URL)
"""
)

adm = re.sub(
r"items\.push\(\{ title: \(title\|\|''\)\.trim\(\), details: \(details\|\|''\)\.trim\(\) \}\);",
r"items.push({ title: (title||'').trim(), details: (details||'').trim(), source_url: (line.split('::').length>2? line.split('::').slice(2).join('::').trim(): undefined) });",
adm
)

open(ADMIN, "w", encoding="utf-8").write(adm)
print("v4.1 per-item source badges + inline editor support added.")
