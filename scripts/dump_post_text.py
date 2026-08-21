#!/usr/bin/env python3
"""Extrai o texto essencial (estrutura) de posts do backup, compacto, pra reescrita.
Uso: python scripts/dump_post_text.py <backup_dir> <id> [<id> ...]"""
import json, sys
from pathlib import Path
SK = Path(__file__).resolve().parent.parent
bdir = SK / "backups" / sys.argv[1]
man = json.loads((bdir / "manifest.json").read_text(encoding="utf-8"))

def inline(nodes):
    out = []
    for n in nodes:
        t = n.get("type")
        if t == "text":
            out.append(n.get("text", ""))
        elif t == "link":
            url = (n.get("fields", {}) or {}).get("url", "")
            out.append(f"[{inline(n.get('children', []))}]({url})")
    return "".join(out)

def walk(node, out):
    for n in node.get("children", []):
        t = n.get("type")
        if t == "heading":
            out.append(f"\n{'#'*int(n.get('tag','h2')[1])} {inline(n.get('children', []))}")
        elif t == "paragraph":
            txt = inline(n.get("children", []))
            if txt.strip():
                out.append(txt)
        elif t == "list":
            for li in n.get("children", []):
                out.append(f"- {inline(li.get('children', []))}")
        elif t == "quote":
            out.append(f"> {inline(n.get('children', []))}")
        elif t == "upload":
            v = n.get("value", {})
            alt = v.get("alt", "") if isinstance(v, dict) else ""
            out.append(f"[IMG: {alt}]")
        elif t == "horizontalrule":
            out.append("---")

outdir = SK / "backups" / "_dump"
outdir.mkdir(exist_ok=True)
for pid in sys.argv[2:]:
    entry = next((p for p in man["posts"] if str(p["id"]) == str(pid)), None)
    if not entry:
        print(f"== post {pid}: não está no backup =="); continue
    doc = json.loads((bdir / entry["locales"]["pt-BR"]).read_text(encoding="utf-8"))
    header = [
        f"ID {pid} | slug: {doc.get('slug')}",
        f"TITLE: {doc.get('title')}",
        f"SEO metaTitle: {(doc.get('seo') or {}).get('metaTitle')}",
        f"SEO metaDesc: {(doc.get('seo') or {}).get('metaDescription')}",
        f"CATEGORIAS: {[c.get('title') if isinstance(c,dict) else c for c in (doc.get('categories') or [])]}",
        "\n--- CONTEÚDO ATUAL ---",
    ]
    out = []
    walk((doc.get("content") or {}).get("root") or {}, out)
    fp = outdir / f"post_{pid}.txt"
    fp.write_text("\n".join(header) + "\n" + "\n".join(out), encoding="utf-8")
    print(f"dump -> backups/_dump/post_{pid}.txt  ({len(out)} blocos)")
