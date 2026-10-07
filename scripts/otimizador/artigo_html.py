# -*- coding: utf-8 -*-
"""Exporta um post publicado (Lexical) para o HTML semântico da skill, para a
otimização editar o texto que está NO AR (e não uma versão antiga do output/).

O HTML sai no formato que o conversor do payload_publish entende:
    <h1>título</h1>
    <p>excerpt</p>          <- o conversor tira o 1º parágrafo do corpo (é o lead)
    ...corpo...
A imagem de capa (featuredImage) não entra: o aplicador não mexe nela.

Uso:
    python scripts/otimizador/artigo_html.py <id> [--de-backup <pasta>]
Saída: otimizador/trabalho/<slug>/original.html, artigo.html (cópia para editar)
e seo.json (metaTitle/metaDescription atuais).
"""
import argparse
import html
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import SKILL_DIR, http, load_env, payload_login  # noqa: E402

TRABALHO = SKILL_DIR / "otimizador" / "trabalho"
BOLD, ITALIC, STRIKE, UNDERLINE, CODE = 1, 2, 4, 8, 16


def texto(no):
    t = html.escape(no.get("text", ""), quote=False)
    f = no.get("format", 0) or 0
    if f & CODE:
        t = f"<code>{t}</code>"
    if f & UNDERLINE:
        t = f"<u>{t}</u>"
    if f & ITALIC:
        t = f"<em>{t}</em>"
    if f & BOLD:
        t = f"<strong>{t}</strong>"
    return t


def inline(filhos):
    out = []
    for n in filhos:
        tipo = n.get("type")
        if tipo == "text":
            out.append(texto(n))
        elif tipo == "linebreak":
            out.append("<br>")
        elif tipo in ("link", "autolink"):
            url = html.escape((n.get("fields") or {}).get("url", "#"))
            out.append(f'<a href="{url}">{inline(n.get("children", []))}</a>')
        else:
            out.append(inline(n.get("children", [])))
    return "".join(out)


def blocos(filhos, midia):
    out = []
    for n in filhos:
        tipo = n.get("type")
        if tipo == "heading":
            tag = n.get("tag", "h2")
            out.append(f"<{tag}>{inline(n.get('children', []))}</{tag}>")
        elif tipo == "paragraph":
            conteudo = inline(n.get("children", []))
            if conteudo.strip():
                out.append(f"<p>{conteudo}</p>")
        elif tipo == "quote":
            # o conversor junta os <p> do blockquote com "\n"; aqui desfaz
            partes = inline(n.get("children", [])).split("\n")
            out.append("<blockquote>" + "".join(f"<p>{p}</p>" for p in partes if p.strip()) + "</blockquote>")
        elif tipo == "list":
            tag = "ol" if n.get("listType") == "number" or n.get("tag") == "ol" else "ul"
            itens = "".join(f"<li>{inline(li.get('children', []))}</li>" for li in n.get("children", []))
            out.append(f"<{tag}>{itens}</{tag}>")
        elif tipo == "horizontalrule":
            out.append("<hr>")
        elif tipo == "upload":
            valor = n.get("value")
            mid = valor.get("id") if isinstance(valor, dict) else valor
            arq, alt = midia(mid)
            out.append(f'<img src="{html.escape(arq)}" alt="{html.escape(alt)}">')
        else:
            raise SystemExit(f"[X] nó Lexical '{tipo}' sem conversão; exportar quebraria o artigo")
    return out


def exportar(doc, midia):
    linhas = [f"<h1>{html.escape(doc['title'], quote=False)}</h1>",
              f"<p>{html.escape(doc.get('excerpt') or '', quote=False)}</p>"]
    linhas += blocos(doc["content"]["root"]["children"], midia)
    return "\n".join(linhas) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--de-backup", help="pasta em backups/ (sem isso, lê o post ao vivo)")
    args = ap.parse_args()

    auth = payload_login(load_env())
    if args.de_backup:
        doc = json.loads((SKILL_DIR / "backups" / args.de_backup / f"post_{args.id}_pt-BR.json")
                         .read_text(encoding="utf-8"))
    else:
        code, doc = http("GET", f"{auth['api']}/api/posts/{args.id}?locale=pt-BR&depth=0",
                         token=auth["token"], scheme=auth["scheme"])
        if code != 200:
            raise SystemExit(f"[X] GET post {args.id}: HTTP {code}")

    cache = {}

    def midia(mid):
        if mid not in cache:
            code, m = http("GET", f"{auth['api']}/api/media/{mid}?depth=0",
                           token=auth["token"], scheme=auth["scheme"])
            if code != 200:
                raise SystemExit(f"[X] mídia {mid} não encontrada (HTTP {code})")
            cache[mid] = (m["filename"], m.get("alt") or "")
        return cache[mid]

    pasta = TRABALHO / doc["slug"]
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "original.html").write_text(exportar(doc, midia), encoding="utf-8")
    if not (pasta / "artigo.html").exists():
        shutil.copy(pasta / "original.html", pasta / "artigo.html")
    seo = doc.get("seo") or {}
    (pasta / "seo.json").write_text(json.dumps({
        "id": doc["id"], "slug": doc["slug"],
        "metaTitle": seo.get("metaTitle") or "", "metaDescription": seo.get("metaDescription") or "",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {pasta}")


if __name__ == "__main__":
    main()
