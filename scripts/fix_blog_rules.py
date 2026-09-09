#!/usr/bin/env python3
"""
fix_blog_rules.py — Aplica nos posts JÁ PUBLICADOS as duas regras duras da skill:

  R1. Nenhuma imagem do blog pode ser logo de marca (hero nem corpo).
  R2. Nenhum link para o PDF direto do estudo. O destino é sempre a página de
      captura https://metakosmos.com.br/estudo, preservando os UTMs do link.

Uso:
    python scripts/fix_blog_rules.py --check                # auditoria read-only
    python scripts/fix_blog_rules.py --fix-links [ids...]   # R2 (sem id = todos)
    python scripts/fix_blog_rules.py --fix-images [ids...]  # R1 (usa IMAGE_SWAPS)

Só faz PATCH no locale pt-BR: é o canônico, en/es fazem fallback (mesma razão
documentada em swap_post_images.py). Rodar backup_all_posts.py antes.
"""
import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
from payload_publish import load_env, http, payload_login  # noqa: E402

ESTUDO_URL = "https://metakosmos.com.br/estudo"
PDF_MARKERS = ("api/media/file/State%20of%20Immersive", "api/media/file/State of Immersive")

# R1 — troca curada de imagem-logo por imagem real do mesmo contexto.
# {post_id: {"featured": "arquivo.webp"|None, "inline": {media_id_antigo: "arquivo.webp"}}}
IMAGE_SWAPS = {
    91: {"inline": {150: "mkbeauty-bioextratus-ia-simulacao-cor-cabelo.webp"}},
    86: {"inline": {610: "metakosmos-cases-reais-colagem-clientes.webp"}},
    4:  {"inline": {610: "metakosmos-cases-reais-colagem-clientes.webp"}},
    77: {"featured": "metakosmos-conceito-immersive-commerce-loja-digital.webp"},
    19: {"featured": "metakosmos-homepage-lider-immersive-commerce.webp"},
}

# Palavras que indicam logo no filename/alt. "catálogo" contém "logo": não conta.
LOGO_RE = re.compile(r"logo", re.I)
FALSE_POSITIVE_RE = re.compile(r"cat[aá]logo|com o logo|com logo|proje[çc]", re.I)


def is_logo(filename, alt):
    fn = FALSE_POSITIVE_RE.sub("", filename or "")
    a = FALSE_POSITIVE_RE.sub("", alt or "")
    return bool(LOGO_RE.search(fn) or LOGO_RE.search(a))


def fetch_all_posts(auth, depth=2):
    posts, page = [], 1
    while True:
        url = f"{auth['api']}/api/posts?limit=100&page={page}&depth={depth}&locale=pt-BR"
        code, r = http("GET", url, token=auth["token"], scheme=auth["scheme"])
        if code != 200:
            sys.exit(f"Erro ao listar posts: HTTP {code}")
        posts += r.get("docs", [])
        if not r.get("hasNextPage"):
            break
        page += 1
    return posts


def fetch_post(auth, pid, depth=0):
    code, d = http("GET", f"{auth['api']}/api/posts/{pid}?depth={depth}&locale=pt-BR",
                   token=auth["token"], scheme=auth["scheme"])
    if code != 200:
        sys.exit(f"Erro ao ler post {pid}: HTTP {code}")
    return d


def find_media_id(auth, filename):
    q = urllib.parse.quote(filename)
    code, r = http("GET", f"{auth['api']}/api/media?where[filename][equals]={q}&limit=1",
                   token=auth["token"], scheme=auth["scheme"])
    docs = r.get("docs") or []
    return (docs[0].get("id"), docs[0].get("alt")) if docs else (None, None)


def walk_nodes(node, kind, fn):
    """Aplica fn em todo nó do tipo `kind` (dict) na árvore Lexical."""
    if isinstance(node, dict):
        if node.get("type") == kind:
            fn(node)
        for v in node.values():
            walk_nodes(v, kind, fn)
    elif isinstance(node, list):
        for v in node:
            walk_nodes(v, kind, fn)


def node_text(node):
    out = []

    def w(x):
        if isinstance(x, dict):
            if x.get("type") == "text":
                out.append(x.get("text", ""))
            for v in (x.get("children") or []):
                w(v)
        elif isinstance(x, list):
            for v in x:
                w(v)

    w(node)
    return "".join(out)


def is_pdf_link(url):
    return any(m in (url or "") for m in PDF_MARKERS)


def rewrite_pdf_url(url):
    """PDF direto -> /estudo, preservando só os utm_* (o prefix=prod/site morre)."""
    qs = urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query, keep_blank_values=True)
    utms = [(k, v) for k, v in qs if k.startswith("utm_")]
    if not utms:
        utms = [("utm_source", "blog"), ("utm_medium", "cta-inline"),
                ("utm_campaign", "state-of-immersive-agentic-commerce-2026")]
    return ESTUDO_URL + "?" + urllib.parse.urlencode(utms)


def cmd_check(auth):
    posts = fetch_all_posts(auth)
    logo_hits, link_hits = [], []
    for p in sorted(posts, key=lambda x: x.get("id")):
        slug, pid = p.get("slug"), p.get("id")
        fi = p.get("featuredImage") or {}
        if isinstance(fi, dict) and is_logo(fi.get("filename"), fi.get("alt")):
            logo_hits.append((pid, slug, "HERO", fi.get("id"), fi.get("filename")))
        uploads = []
        walk_nodes(p.get("content"), "upload", lambda n: uploads.append(n.get("value") or {}))
        for v in uploads:
            if isinstance(v, dict) and is_logo(v.get("filename"), v.get("alt")):
                logo_hits.append((pid, slug, "CORPO", v.get("id"), v.get("filename")))
        links = []
        walk_nodes(p.get("content"), "link", lambda n: links.append(n))
        for n in links:
            u = (n.get("fields") or {}).get("url", "")
            if is_pdf_link(u):
                link_hits.append((pid, slug, node_text(n)[:60]))

    print("\n=== R1: imagem-logo ===")
    for h in logo_hits:
        print("  ", h)
    print(f"  total: {len(logo_hits)} ocorrências")
    print("\n=== R2: link direto do PDF do estudo ===")
    for h in link_hits:
        print("  ", h)
    print(f"  total: {len(link_hits)} ocorrências em {len({h[0] for h in link_hits})} posts")
    return logo_hits, link_hits


def cmd_fix_links(auth, ids):
    posts = fetch_all_posts(auth, depth=0)
    alvo = [p for p in posts if (not ids or p.get("id") in ids)]
    ok = 0
    for p in alvo:
        pid = p.get("id")
        d = fetch_post(auth, pid)
        content = d.get("content")
        changed = []

        def fix(n):
            f = n.get("fields") or {}
            u = f.get("url", "")
            if is_pdf_link(u):
                novo = rewrite_pdf_url(u)
                f["url"] = novo
                n["fields"] = f
                changed.append(novo)

        walk_nodes(content, "link", fix)
        if not changed:
            continue
        code, r = http("PATCH", f"{auth['api']}/api/posts/{pid}?locale=pt-BR",
                       body={"content": content}, token=auth["token"], scheme=auth["scheme"])
        if code in (200, 201):
            ok += 1
            print(f"  [OK] {pid} {p.get('slug')}: {len(changed)} link(s) -> {changed[0][:80]}")
        else:
            print(f"  [X] {pid} {p.get('slug')}: HTTP {code} {json.dumps(r, ensure_ascii=False)[:200]}")
    print(f"\nR2: {ok} posts corrigidos")


def cmd_fix_images(auth, ids):
    ok = 0
    for pid, spec in IMAGE_SWAPS.items():
        if ids and pid not in ids:
            continue
        d = fetch_post(auth, pid)
        body = {}
        if spec.get("featured"):
            mid, alt = find_media_id(auth, spec["featured"])
            if not mid:
                print(f"  [X] {pid}: mídia '{spec['featured']}' não existe na Media")
                continue
            body["featuredImage"] = mid
        inline = spec.get("inline") or {}
        if inline:
            content = d.get("content")
            trocas = []
            resolvidos = {}
            for old_id, fname in inline.items():
                mid, alt = find_media_id(auth, fname)
                if not mid:
                    print(f"  [X] {pid}: mídia '{fname}' não existe na Media")
                    break
                resolvidos[old_id] = mid
            else:
                def swap(n):
                    v = n.get("value")
                    vid = v.get("id") if isinstance(v, dict) else v
                    if vid in resolvidos:
                        n["value"] = resolvidos[vid]
                        trocas.append((vid, resolvidos[vid]))

                walk_nodes(content, "upload", swap)
                if not trocas:
                    print(f"  [!] {pid}: nenhum slot inline bateu (já corrigido?)")
                body["content"] = content
        if not body:
            continue
        code, r = http("PATCH", f"{auth['api']}/api/posts/{pid}?locale=pt-BR",
                       body=body, token=auth["token"], scheme=auth["scheme"])
        if code in (200, 201):
            ok += 1
            print(f"  [OK] {pid} {d.get('slug')}: {list(body.keys())}")
        else:
            print(f"  [X] {pid}: HTTP {code} {json.dumps(r, ensure_ascii=False)[:200]}")
    print(f"\nR1: {ok} posts corrigidos")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fix-links", action="store_true")
    ap.add_argument("--fix-images", action="store_true")
    ap.add_argument("ids", nargs="*", type=int)
    a = ap.parse_args()
    auth = payload_login(load_env())
    if a.check or not (a.fix_links or a.fix_images):
        cmd_check(auth)
    if a.fix_links:
        cmd_fix_links(auth, set(a.ids))
    if a.fix_images:
        cmd_fix_images(auth, set(a.ids))


if __name__ == "__main__":
    main()
