#!/usr/bin/env python3
"""
sync_payload_lists.py — Porta os artigos e mKases publicados no Payload para a skill.

Puxa TODOS os docs de /api/posts e /api/mkases e gera:
  references/blog-links.md   (artigos publicados, URL real /blog/<slug>)
  references/mkases.md       (mKases publicados, URL real /mkases/<slug>)

Substitui os arquivos homônimos da era WordPress (que apontavam para URLs
que hoje dão 404). Roda rápido (paginado, poucas dezenas/centenas de docs).

Uso: python scripts/sync_payload_lists.py
"""
import json, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ENV = {}
for line in (SKILL / ".env").read_text(encoding="utf-8-sig").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); ENV[k.strip()] = v.strip()
API = ENV["PAYLOAD_API_URL"].rstrip("/")

def http(method, url, body=None, token=None):
    h = {"Accept": "application/json", "User-Agent": "sync/1"}
    if token: h["Authorization"] = f"JWT {token}"
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode("utf-8"); h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=90) as r:
        d = r.read().decode("utf-8"); return r.status, (json.loads(d) if d else {})

_, login = http("POST", f"{API}/api/users/login",
                 body={"email": ENV["PAYLOAD_EMAIL"], "password": ENV["PAYLOAD_PASSWORD"]})
TOKEN = login["token"]

def fetch_all(collection, extra_qs=""):
    items, page = [], 1
    while True:
        _, resp = http("GET", f"{API}/api/{collection}?limit=100&page={page}&depth=0{extra_qs}", token=TOKEN)
        items.extend(resp.get("docs", []))
        if not resp.get("hasNextPage"):
            break
        page += 1
    return items

def write_list(filename, title, collection, base_path, items, extra_cols=None):
    lines = [
        f"# {title}",
        "",
        f"Total: **{len(items)}** publicados. Gerado por `scripts/sync_payload_lists.py` "
        f"a partir de `/api/{collection}`.",
        "",
        f"| slug | título | URL |" + ("".join(f" {c} |" for c in (extra_cols or []))),
        "|---|---|---|" + ("".join("---|" for _ in (extra_cols or []))),
    ]
    for it in sorted(items, key=lambda d: (d.get("slug") or "")):
        slug = it.get("slug") or "?"
        title_v = (it.get("title") or "").replace("|", "/")[:80]
        url = f"{base_path}/{slug}"
        extra = "".join(f" {it.get(c, '') or ''} |" for c in (extra_cols or []))
        lines.append(f"| `{slug}` | {title_v} | {url} |{extra}")
    (SKILL / "references" / filename).write_text("\n".join(lines), encoding="utf-8")

posts = fetch_all("posts", extra_qs="&where[_status][equals]=published")
mkases = fetch_all("mkases", extra_qs="&where[_status][equals]=published")

write_list("blog-links.md", "Artigos publicados no blog (Payload)", "posts", "/blog", posts)
write_list("mkases.md", "mKases publicados (Payload)", "mkases", "/mkases", mkases)

stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
print(f"OK [{stamp}]: {len(posts)} artigos -> references/blog-links.md")
print(f"OK [{stamp}]: {len(mkases)} mKases -> references/mkases.md")
