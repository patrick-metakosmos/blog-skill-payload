#!/usr/bin/env python3
"""
sync_payload_media.py — Porta o catálogo da Media do Payload para a skill.

Puxa TODAS as mídias de /api/media e gera:
  references/media-payload.json  (dados completos: id, filename, alt, dims, orientação, url)
  references/media-payload.md    (catálogo legível pra skill escolher imagens reais)

A skill referencia imagens por NOME DE ARQUIVO no artigo.html; o payload_publish.py
resolve o ID pela Media. Só use nomes que aparecem neste catálogo.

Uso: python scripts/sync_payload_media.py
"""
import json, urllib.request, urllib.error
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ENV = {}
for line in (SKILL / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); ENV[k.strip()] = v.strip()
API = ENV["PAYLOAD_API_URL"].rstrip("/")

def http(method, url, body=None, token=None):
    h = {"Accept":"application/json","User-Agent":"sync/1"}
    if token: h["Authorization"] = f"JWT {token}"
    if isinstance(body,(dict,list)):
        body=json.dumps(body).encode("utf-8"); h["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=body,method=method,headers=h)
    with urllib.request.urlopen(req,timeout=90) as r:
        d=r.read().decode("utf-8"); return r.status,(json.loads(d) if d else {})

_, login = http("POST", f"{API}/api/users/login", body={"email":ENV["PAYLOAD_EMAIL"],"password":ENV["PAYLOAD_PASSWORD"]})
TOKEN = login["token"]

def orient(w, h):
    if not w or not h: return "?"
    if h >= w * 1.15: return "vertical"
    if w >= h * 1.15: return "horizontal"
    return "quadrada"

items, page = [], 1
while True:
    _, resp = http("GET", f"{API}/api/media?limit=100&page={page}&depth=0&sort=filename", token=TOKEN)
    docs = resp.get("docs", [])
    for d in docs:
        items.append({
            "id": d.get("id"),
            "filename": d.get("filename"),
            "alt": (d.get("alt") or "").strip(),
            "width": d.get("width"),
            "height": d.get("height"),
            "orient": orient(d.get("width"), d.get("height")),
            "mime": d.get("mimeType"),
            "filesize": d.get("filesize"),
            "url": d.get("url"),
        })
    if not resp.get("hasNextPage"):
        break
    page += 1

items.sort(key=lambda x: (x["filename"] or "").lower())
(SKILL / "references" / "media-payload.json").write_text(
    json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

# markdown
lines = [
    "# Catálogo da Media do Payload (fonte de imagens reais)",
    "",
    f"Total: **{len(items)}** mídias. Gerado por `scripts/sync_payload_media.py`.",
    "",
    "**Como usar:** no `artigo.html`, referencie a imagem pelo NOME DE ARQUIVO exato da coluna `filename`",
    "(ex: `<img src=\"mK3DShop-Flexform.gif\" alt=\"...\">`). O publicador resolve o ID na Media.",
    "Só use nomes que aparecem aqui. **Todas as imagens renderizam full-width** (o tema não flutua imagem em coluna).",
    "Para hero/featured, prefira uma imagem **horizontal**.",
    "",
    "| filename | orient | dims | KB | alt |",
    "|---|---|---|---|---|",
]
for it in items:
    dims = f"{it['width']}x{it['height']}" if it['width'] else "?"
    kb = f"{it['filesize']//1024}" if it.get('filesize') else "?"
    alt = (it["alt"] or "").replace("|", "/")[:80]
    lines.append(f"| `{it['filename']}` | {it['orient']} | {dims} | {kb} | {alt} |")
(SKILL / "references" / "media-payload.md").write_text("\n".join(lines), encoding="utf-8")

by_o = {}
for it in items: by_o[it["orient"]] = by_o.get(it["orient"],0)+1
big = [it for it in items if (it.get("filesize") or 0) > 2*1024*1024]
total_kb = sum((it.get("filesize") or 0) for it in items) // 1024
print(f"OK: {len(items)} mídias -> references/media-payload.(json|md)")
print(f"orientação: {by_o}")
print(f"tamanho total: {total_kb} KB | acima de 2MB: {len(big)}")
if big:
    for it in sorted(big, key=lambda x: -(x.get('filesize') or 0))[:15]:
        print(f"  {(it['filesize']//1024):>6} KB  {it['filename']}")
