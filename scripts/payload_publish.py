#!/usr/bin/env python3
"""
payload_publish.py — Modo Publicar (Payload CMS) da skill blog-mk

Sucessor do wp_publish.py para o novo CMS (Payload) em metakosmos.com.br.
Converte o artigo Gutenberg (output/[slug]/artigo.html) para o formato
Lexical (JSON) que o Payload usa no campo `content`, e cria o post via
REST API (POST /api/posts) como rascunho.

Diferenças estruturais vs WordPress (ver reference_payload_posts_schema):
- Corpo = árvore Lexical {"root":{"children":[...]}}, NÃO HTML Gutenberg.
- Payload usa só primitivos: paragraph, heading, list, link, upload,
  horizontalrule, text (bold=format 1). Cards/botões/colunas/cores do
  Gutenberg são ACHATADOS para parágrafo/lista simples.
- Imagens = nós `upload` referenciando a coleção `media` por ID.
- Relacionamentos (featuredImage, categories, tags) por ID.
- SEO = grupo {metaTitle, metaDescription, noIndex} (sem Yoast focuskw/cornerstone).
- i18n: 1 locale por vez (?locale=pt-BR; PATCH ?locale=en/es depois).
- Auth: POST /api/users/login {email,password} -> header "Authorization: JWT <token>".

Uso:
    python scripts/payload_publish.py --list
    python scripts/payload_publish.py <slug> --dry-run            # converte e mostra, SEM API
    python scripts/payload_publish.py <slug> --dry-run --emit-json out.json
    python scripts/payload_publish.py <slug> --probe               # testa auth + schema (precisa .env)
    python scripts/payload_publish.py <slug>                       # cria rascunho no Payload
    python scripts/payload_publish.py <slug> --status published    # publica direto (cuidado!)

.env (em blog mK/.env), adicionar:
    PAYLOAD_API_URL=https://metakosmos.com.br
    PAYLOAD_EMAIL=seu-email-do-admin
    PAYLOAD_PASSWORD=sua-senha
    # opcional, se o time preferir API Key em vez de login:
    # PAYLOAD_API_KEY=...
    # PAYLOAD_AUTH_COLLECTION=users
"""

import argparse
import html as html_lib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

# === Config ===
SKILL_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = SKILL_DIR / "output"
ENV_FILE = SKILL_DIR / ".env"
USER_AGENT = "blog-mk-skill-payload/0.1"

# Categorias reais do Payload (id | title | slug), confirmadas via API 2026-07:
#   1 Estudos de caso / estudos-de-caso   2 Guias / guias   3 História / historia
#   4 mKases / mkcases-tag   5 Notícias / noticias   6 Podcast / podcast
#   7 Provador Virtual / provador-virtual   8 Visualizador 3D & AR / visualizador-3d-ar
#   9 Immersive Commerce / immersive-commerce
# Pilar (metadados) -> slug de categoria (resolução primária):
PILAR_TO_CATEGORY_SLUG = {
    1: "immersive-commerce",
    2: "provador-virtual",
    3: "visualizador-3d-ar",
    6: "mkcases-tag",
}
# Nome da categoria (metadados) -> slug (fallback quando slugify não bate):
CATEGORY_NAME_TO_SLUG = {
    "Immersive Commerce": "immersive-commerce",
    "Provador Virtual": "provador-virtual",
    "Visualizador 3D e Realidade Aumentada": "visualizador-3d-ar",
    "Visualizador 3D e AR": "visualizador-3d-ar",
    "mKases": "mkcases-tag",
    "Guias": "guias",
}

VOID_TAGS = {"img", "hr", "br", "input", "meta", "link", "source"}
INLINE_TAGS = {"strong", "b", "em", "i", "u", "a", "span", "code", "br", "mark", "sub", "sup"}
FORMAT_BOLD = 1
FORMAT_ITALIC = 2
FORMAT_UNDERLINE = 8


def log(msg, level="info"):
    prefix = {"info": "[i]", "ok": "[OK]", "warn": "[!]", "err": "[X]"}.get(level, "[i]")
    print(f"{prefix} {msg}")


# =====================================================================
# MiniDOM — parser HTML leve (ignora comentários <!-- wp:... -->)
# =====================================================================
class Node:
    __slots__ = ("tag", "attrs", "children", "text")

    def __init__(self, tag=None, attrs=None, text=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.text = text  # só para nós de texto (tag=None)


class DOMBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag=tag, attrs=attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag=tag, attrs=attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(Node(text=data))

    # comentários (blocos wp:) são ignorados de propósito


def parse_html(html):
    b = DOMBuilder()
    b.feed(html)
    return b.root


# =====================================================================
# Lexical builders (formatos exatos observados no post real)
# =====================================================================
def lex_text(text, fmt=0):
    return {"mode": "normal", "text": text, "type": "text", "style": "",
            "detail": 0, "format": fmt, "version": 1}


def lex_paragraph(children):
    return {"type": "paragraph", "format": "", "indent": 0, "version": 1,
            "children": children, "direction": "ltr", "textStyle": "", "textFormat": 0}


def lex_heading(tag, children):
    return {"tag": tag, "type": "heading", "format": "", "indent": 0, "version": 1,
            "children": children, "direction": "ltr"}


def lex_link(url, children, new_tab=True):
    return {"type": "link", "fields": {"url": url, "newTab": new_tab, "linkType": "custom"},
            "format": "", "indent": 0, "version": 3, "children": children, "direction": "ltr"}


def lex_listitem(children, value):
    return {"type": "listitem", "value": value, "format": "", "indent": 0, "version": 1,
            "children": children, "direction": "ltr"}


def lex_list(items, ordered=False):
    return {"tag": "ol" if ordered else "ul", "type": "list", "start": 1, "format": "",
            "indent": 0, "version": 1, "children": items,
            "listType": "number" if ordered else "bullet", "direction": "ltr"}


def lex_hr():
    return {"type": "horizontalrule", "version": 1}


def lex_quote(children):
    # bloco de citação — renderiza como CAIXA de destaque no tema do Payload
    return {"type": "quote", "format": "", "indent": 0, "version": 1,
            "children": children, "direction": "ltr"}


def lex_upload(media_id):
    return {"type": "upload", "value": media_id, "fields": None, "format": "",
            "version": 3, "relationTo": "media"}


def lex_root(children):
    return {"root": {"type": "root", "format": "", "indent": 0, "version": 1,
                     "children": children, "direction": "ltr"}}


# =====================================================================
# Conversão HTML -> Lexical
# =====================================================================
class Converter:
    def __init__(self):
        self.images = []          # basenames de imagens encontradas (para resolver IDs)
        self.hero_filename = None # primeira imagem antes de qualquer parágrafo

    @staticmethod
    def _img_basename(src):
        # Nome EXATO do arquivo (Payload guarda o nome como está — NÃO remover
        # sufixos -NxM/-scaled: no Payload eles fazem parte do filename real).
        return html_lib.unescape(src.rsplit("/", 1)[-1].split("?", 1)[0])

    def inline(self, node, fmt=0):
        """Converte filhos inline de um elemento em nós Lexical (text/link)."""
        out = []
        for child in node.children:
            if child.tag is None:
                txt = child.text
                if txt.strip() == "" and not out:
                    # ignora whitespace de indentação no começo
                    if not txt.strip():
                        continue
                out.append(lex_text(txt, fmt))
            elif child.tag in ("strong", "b"):
                out.extend(self.inline(child, fmt | FORMAT_BOLD))
            elif child.tag in ("em", "i"):
                out.extend(self.inline(child, fmt | FORMAT_ITALIC))
            elif child.tag == "u":
                out.extend(self.inline(child, fmt | FORMAT_UNDERLINE))
            elif child.tag == "a":
                url = html_lib.unescape(child.attrs.get("href", "#"))
                kids = self.inline(child, fmt) or [lex_text(_node_text(child), fmt)]
                out.append(lex_link(url, kids))
            elif child.tag == "br":
                out.append(lex_text("\n", fmt))
            elif child.tag in ("span", "code", "mark", "sub", "sup"):
                out.extend(self.inline(child, fmt))
            else:
                # elemento inesperado inline: puxa o texto
                t = _node_text(child)
                if t.strip():
                    out.append(lex_text(t, fmt))
        # limpa nós de texto totalmente vazios nas bordas
        return [n for n in out if not (n["type"] == "text" and n["text"] == "")]

    def _first_img(self, node):
        for c in node.children:
            if c.tag == "img":
                return c
            if c.tag in ("figure", "div", "span", "a"):
                found = self._first_img(c)
                if found:
                    return found
        return None

    def blocks(self, node, top_level=False, seen_paragraph_ref=None):
        """Converte filhos de bloco de `node` numa lista de nós Lexical de bloco."""
        out = []
        if seen_paragraph_ref is None:
            seen_paragraph_ref = [False]
        for child in node.children:
            if child.tag is None:
                continue  # whitespace entre blocos
            tag = child.tag

            if tag in ("script", "style", "svg"):
                continue
            if tag == "h1":
                continue  # vira o título do post
            if tag in ("h2", "h3", "h4", "h5", "h6"):
                kids = self.inline(child)
                if kids:
                    out.append(lex_heading(tag, kids))
            elif tag == "p":
                kids = self.inline(child)
                if kids:
                    out.append(lex_paragraph(kids))
                    seen_paragraph_ref[0] = True
            elif tag in ("ul", "ol"):
                items = []
                idx = 0
                for li in child.children:
                    if li.tag == "li":
                        idx += 1
                        kids = self.inline(li)
                        if kids:
                            items.append(lex_listitem(kids, idx))
                if items:
                    out.append(lex_list(items, ordered=(tag == "ol")))
                    seen_paragraph_ref[0] = True
            elif tag == "hr":
                out.append(lex_hr())
            elif tag in ("figure", "img"):
                img = child if tag == "img" else self._first_img(child)
                if img is not None:
                    src = img.attrs.get("src", "")
                    base = self._img_basename(src)
                    # hero = 1ª imagem antes de qualquer parágrafo
                    if top_level and not seen_paragraph_ref[0] and self.hero_filename is None:
                        self.hero_filename = base
                    else:
                        self.images.append(base)
                        out.append(lex_upload({"__filename__": base}))
                # legenda do figure -> parágrafo
                cap = _find_tag(child, "figcaption")
                if cap is not None:
                    kids = self.inline(cap)
                    if kids:
                        out.append(lex_paragraph(kids))
            elif tag == "blockquote":
                # <blockquote> -> nó quote (renderiza como CAIXA de destaque no tema)
                q_children = []
                for c in child.children:
                    if c.tag == "p":
                        if q_children:
                            q_children.append(lex_text("\n"))
                        q_children.extend(self.inline(c))
                    elif c.tag is None:
                        continue
                    elif c.tag in INLINE_TAGS or c.tag is None:
                        q_children.extend(self.inline(child))
                if not q_children:
                    q_children = self.inline(child)
                if q_children:
                    out.append(lex_quote(q_children))
                    seen_paragraph_ref[0] = True
            elif tag in ("div", "section", "article", "main"):
                # containers Gutenberg (group/columns/column): transparente, achata
                out.extend(self.blocks(child, top_level=False, seen_paragraph_ref=seen_paragraph_ref))
            elif tag == "a" and "wp-block-button__link" in child.attrs.get("class", ""):
                # botão CTA -> parágrafo com link (melhor que perder o link)
                url = html_lib.unescape(child.attrs.get("href", "#"))
                kids = self.inline(child) or [lex_text(_node_text(child))]
                out.append(lex_paragraph([lex_link(url, kids)]))
                seen_paragraph_ref[0] = True
            elif tag == "table":
                # sem nó de tabela confirmado -> achata linhas em parágrafos
                for row_txt in _table_rows_text(child):
                    out.append(lex_paragraph([lex_text(row_txt)]))
            else:
                # fallback: tenta processar filhos como blocos
                out.extend(self.blocks(child, top_level=False, seen_paragraph_ref=seen_paragraph_ref))
        return out

    def convert(self, html):
        root = parse_html(html)
        body = self.blocks(root, top_level=True)
        return lex_root(body)


def _node_text(node):
    if node.tag is None:
        return node.text or ""
    return "".join(_node_text(c) for c in node.children)


def _find_tag(node, tag):
    for c in node.children:
        if c.tag == tag:
            return c
        found = _find_tag(c, tag)
        if found is not None:
            return found
    return None


def _table_rows_text(table):
    rows = []
    for tr in _iter_tags(table, "tr"):
        cells = [_node_text(td).strip() for td in tr.children if td.tag in ("td", "th")]
        cells = [c for c in cells if c]
        if cells:
            rows.append(" | ".join(cells))
    return rows


def _iter_tags(node, tag):
    for c in node.children:
        if c.tag == tag:
            yield c
        yield from _iter_tags(c, tag)


# =====================================================================
# metadados.md
# =====================================================================
def parse_metadados(md_path):
    text = md_path.read_text(encoding="utf-8")

    def extract(pattern, default=None):
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1).strip() if m else default

    def clean_size(s):
        return re.sub(r"\s*\(\d+\s*caracteres?\)\s*$", "", s).strip() if s else s

    title_seo = clean_size(extract(r"\*\*Título SEO:\*\*\s*(.+)"))
    meta_desc = clean_size(extract(r"\*\*Meta Description:\*\*\s*(.+)"))
    slug = extract(r"\*\*Slug:\*\*\s*(\S+)")
    cat = extract(r"\*\*Categoria:\*\*\s*(.+)")
    pilar_str = extract(r"\*\*Pilar:\*\*\s*(\d+)")
    pilar = int(pilar_str) if pilar_str else None
    tags_str = extract(r"\*\*Tags:\*\*\s*(.+)")
    tags = [t.strip() for t in (tags_str or "").split(",") if t.strip()]
    return {
        "title_seo": title_seo or "",
        "meta_description": meta_desc or "",
        "slug": slug or "",
        "category_name": cat or "",
        "pilar": pilar,
        "tags": tags,
    }


# H1 do artigo -> title do post
def extract_h1_title(html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    return html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


# excerpt = 1º parágrafo INTEIRO (frases completas, sem cortar). No formato novo o
# parágrafo já é curto (<=40 palavras). Ele é removido do corpo (build_content) para
# não repetir embaixo do lead.
def extract_excerpt(html):
    m = re.search(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    return html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


# =====================================================================
# Env / API
# =====================================================================
def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def http(method, url, headers=None, body=None, token=None, scheme="JWT"):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", USER_AGENT)
    headers.setdefault("Accept", "application/json")
    if token:
        headers["Authorization"] = f"{scheme} {token}"
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read().decode("utf-8")
            return r.status, (json.loads(data) if data else {})
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"raw_error": "non-json"}
    except urllib.error.URLError as e:
        return 0, {"error": str(e)}


def payload_login(env):
    api = env["PAYLOAD_API_URL"].rstrip("/")
    coll = env.get("PAYLOAD_AUTH_COLLECTION", "users")
    if env.get("PAYLOAD_API_KEY"):
        log("Usando API Key", "ok")
        return {"scheme": f"{coll} API-Key", "token": env["PAYLOAD_API_KEY"], "api": api}
    log("Autenticando via /login...")
    code, resp = http("POST", f"{api}/api/{coll}/login",
                      body={"email": env["PAYLOAD_EMAIL"], "password": env["PAYLOAD_PASSWORD"]})
    if code in (200, 201) and resp.get("token"):
        log(f"Token obtido (user: {resp.get('user', {}).get('email', '?')})", "ok")
        return {"scheme": env.get("PAYLOAD_AUTH_SCHEME", "JWT"), "token": resp["token"], "api": api}
    log(f"Login falhou (HTTP {code}): {json.dumps(resp, ensure_ascii=False)[:300]}", "err")
    sys.exit(1)


def find_media_id(auth, filename):
    q = urllib.parse.quote(filename)
    url = f"{auth['api']}/api/media?where[filename][equals]={q}&limit=1"
    code, resp = http("GET", url, token=auth["token"], scheme=auth["scheme"])
    docs = resp.get("docs") if isinstance(resp, dict) else None
    if docs:
        return docs[0]["id"]
    return None


def resolve_relation(auth, collection, slug=None, title=None, create_title=None):
    api = auth["api"]
    if slug:
        code, resp = http("GET", f"{api}/api/{collection}?where[slug][equals]={urllib.parse.quote(slug)}&limit=1",
                          token=auth["token"], scheme=auth["scheme"])
        docs = resp.get("docs") if isinstance(resp, dict) else None
        if docs:
            return docs[0]["id"]
    if title:
        code, resp = http("GET", f"{api}/api/{collection}?where[title][equals]={urllib.parse.quote(title)}&limit=1",
                          token=auth["token"], scheme=auth["scheme"])
        docs = resp.get("docs") if isinstance(resp, dict) else None
        if docs:
            return docs[0]["id"]
    if create_title:
        code, resp = http("POST", f"{api}/api/{collection}",
                          body={"title": create_title, "slug": slugify(create_title)},
                          token=auth["token"], scheme=auth["scheme"])
        if code in (200, 201):
            doc = resp.get("doc", resp)
            log(f"  {collection} criada: '{create_title}' -> ID {doc.get('id')}")
            return doc.get("id")
        log(f"  falha ao criar {collection} '{create_title}' (HTTP {code}): "
            f"{json.dumps(resp, ensure_ascii=False)[:160]}", "warn")
    return None


def slugify(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# =====================================================================
# Build + publish
# =====================================================================
def build_content(article_dir):
    html_path = article_dir / "artigo.html"
    html = html_path.read_text(encoding="utf-8")
    conv = Converter()
    content = conv.convert(html)
    title = extract_h1_title(html)
    excerpt = extract_excerpt(html)
    # lead: o 1º parágrafo é o excerpt e SAI do corpo (não repete embaixo do lead)
    kids = content["root"]["children"]
    if kids and isinstance(kids[0], dict) and kids[0].get("type") == "paragraph":
        kids.pop(0)
    return content, conv, title, excerpt


def resolve_images(auth, content, conv):
    """Substitui placeholders {__filename__} por IDs de mídia reais. Retorna (n_ok, n_missing)."""
    cache = {}
    missing = []

    def resolve(node):
        if isinstance(node, dict):
            if node.get("type") == "upload" and isinstance(node.get("value"), dict):
                fn = node["value"].get("__filename__")
                if fn not in cache:
                    cache[fn] = find_media_id(auth, fn)
                mid = cache[fn]
                if mid:
                    node["value"] = mid
                else:
                    missing.append(fn)
                    node["__drop__"] = True
            for v in node.values():
                resolve(v)
        elif isinstance(node, list):
            for v in node:
                resolve(v)

    resolve(content)

    # remove uploads não resolvidos
    def prune(children):
        return [c for c in children if not (isinstance(c, dict) and c.get("__drop__"))]

    content["root"]["children"] = prune(content["root"]["children"])
    n_ok = sum(1 for f, v in cache.items() if v)
    return n_ok, missing


def find_article_dir(slug):
    """Procura output/[slug] e também output/<Arquivo>/[slug] (Postado, etc.)."""
    direct = OUTPUT_DIR / slug
    if (direct / "artigo.html").exists():
        return direct
    for sub in ("Postado", "Arquivado", "Drafts"):
        cand = OUTPUT_DIR / sub / slug
        if (cand / "artigo.html").exists():
            return cand
    return None


def publish(slug, status="draft", dry_run=False, emit_json=None, probe=False, locale="pt-BR", update_id=None):
    article_dir = find_article_dir(slug)
    if article_dir is None:
        log(f"artigo.html não encontrado para slug '{slug}' em output/ (nem em Postado/)", "err")
        sys.exit(1)
    md_path = article_dir / "metadados.md"
    meta = parse_metadados(md_path) if md_path.exists() else {
        "title_seo": "", "meta_description": "", "slug": slug, "category_name": "", "tags": []}

    content, conv, h1_title, excerpt = build_content(article_dir)

    n_para = _count_type(content, "paragraph")
    n_head = _count_type(content, "heading")
    n_list = _count_type(content, "list")
    n_link = _count_type(content, "link")
    n_up = _count_type(content, "upload")
    log(f"Slug: {meta['slug'] or slug}")
    log(f"Título (H1): {h1_title}")
    log(f"Título SEO ({len(meta['title_seo'])}c): {meta['title_seo']}")
    log(f"Lexical: {n_para} parágrafos, {n_head} headings, {n_list} listas, "
        f"{n_link} links, {n_up} imagens inline")
    log(f"Hero (featuredImage candidata): {conv.hero_filename}")

    if dry_run:
        log("=== DRY RUN — nenhuma chamada à API ===", "warn")
        out = emit_json or (article_dir / "payload.dryrun.json")
        Path(out).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"Lexical gerado salvo em: {out}", "ok")
        return

    env = load_env()
    for k in ("PAYLOAD_API_URL",):
        if not env.get(k):
            log(f"Falta {k} no .env ({ENV_FILE})", "err")
            sys.exit(1)
    if not env.get("PAYLOAD_API_KEY") and not (env.get("PAYLOAD_EMAIL") and env.get("PAYLOAD_PASSWORD")):
        log("Falta PAYLOAD_EMAIL/PAYLOAD_PASSWORD (ou PAYLOAD_API_KEY) no .env", "err")
        sys.exit(1)

    auth = payload_login(env)

    if probe:
        log("=== PROBE — testando coleções ===", "warn")
        for coll in ("posts", "categories", "tags", "media"):
            code, resp = http("GET", f"{auth['api']}/api/{coll}?limit=1",
                              token=auth["token"], scheme=auth["scheme"])
            total = resp.get("totalDocs") if isinstance(resp, dict) else "?"
            log(f"  /api/{coll}: HTTP {code}, totalDocs={total}")
        return

    # imagens -> IDs
    n_ok, missing = resolve_images(auth, content, conv)
    log(f"Imagens inline resolvidas: {n_ok} OK, {len(missing)} não encontradas na Media", "ok")
    if missing:
        log(f"  faltando (removidas do corpo): {', '.join(missing[:6])}", "warn")

    featured_id = find_media_id(auth, conv.hero_filename) if conv.hero_filename else None
    if conv.hero_filename and not featured_id:
        log("Hero não encontrada na Media — post sai sem featuredImage (defina no admin)", "warn")

    # categoria: pilar (primário) -> mapa de nomes -> slugify do nome
    cat_slug = (PILAR_TO_CATEGORY_SLUG.get(meta.get("pilar"))
                or CATEGORY_NAME_TO_SLUG.get(meta["category_name"])
                or (slugify(meta["category_name"]) if meta["category_name"] else None))
    cat_id = resolve_relation(auth, "categories", slug=cat_slug, title=meta["category_name"]) if cat_slug else None
    if cat_slug and not cat_id:
        log(f"Categoria (slug '{cat_slug}') não encontrada no Payload (post sai sem categoria)", "warn")
    elif cat_id:
        log(f"Categoria: slug '{cat_slug}' -> ID {cat_id}", "ok")

    # tags
    tag_ids = []
    for name in meta["tags"]:
        tid = resolve_relation(auth, "tags", slug=slugify(name), title=name, create_title=name)
        if tid:
            tag_ids.append(tid)
    log(f"Tags resolvidas: {len(tag_ids)}/{len(meta['tags'])}")

    payload = {
        "title": h1_title or meta["title_seo"] or meta["slug"],
        "slug": meta["slug"] or slug,
        "excerpt": excerpt,
        "content": content,
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "seo": {
            "metaTitle": meta["title_seo"],
            "metaDescription": meta["meta_description"],
            "noIndex": False,
        },
        "_status": status,
    }
    if featured_id:
        payload["featuredImage"] = featured_id

    if update_id:
        draft_q = "" if status == "published" else "&draft=true"
        estado = "AO VIVO" if status == "published" else "rascunho"
        url = f"{auth['api']}/api/posts/{update_id}?locale={locale}{draft_q}"
        log(f"Atualizando post {update_id} ({estado}) em {url}...")
        code, resp = http("PATCH", url, body=payload, token=auth["token"], scheme=auth["scheme"])
    else:
        draft_q = "&draft=true" if status == "draft" else ""
        url = f"{auth['api']}/api/posts?locale={locale}{draft_q}"
        log(f"Criando post ({status}) em {url}...")
        code, resp = http("POST", url, body=payload, token=auth["token"], scheme=auth["scheme"])
    if code in (200, 201):
        doc = resp.get("doc", resp)
        pid = doc.get("id")
        log(f"Post criado! ID {pid}", "ok")
        log(f"Editor: {auth['api']}/admin/collections/posts/{pid}", "ok")
    else:
        log(f"Erro HTTP {code}: {json.dumps(resp, ensure_ascii=False)[:600]}", "err")
        sys.exit(1)


def _count_type(obj, t):
    n = 0
    if isinstance(obj, dict):
        if obj.get("type") == t:
            n += 1
        for v in obj.values():
            n += _count_type(v, t)
    elif isinstance(obj, list):
        for v in obj:
            n += _count_type(v, t)
    return n


def main():
    p = argparse.ArgumentParser(description="Publica artigo do blog-mk no Payload CMS")
    p.add_argument("slug", nargs="?")
    p.add_argument("--status", choices=["draft", "published"], default="draft")
    p.add_argument("--dry-run", action="store_true", help="Converte e salva o Lexical, sem API")
    p.add_argument("--emit-json", help="Caminho do JSON de saída no dry-run")
    p.add_argument("--probe", action="store_true", help="Testa auth e coleções")
    p.add_argument("--locale", default="pt-BR")
    p.add_argument("--update", type=int, metavar="ID", help="atualiza post existente (PATCH rascunho)")
    p.add_argument("--list", action="store_true")
    args = p.parse_args()

    if args.list:
        ARCH = {"Postado", "Arquivado", "Drafts"}
        slugs = [d.name for d in sorted(OUTPUT_DIR.iterdir())
                 if d.is_dir() and not d.name.startswith("_") and d.name not in ARCH
                 and (d / "artigo.html").exists()]
        log(f"Artigos em output/ ({len(slugs)}):")
        for s in slugs:
            print(f"  {s}")
        return

    if not args.slug:
        p.error("slug é obrigatório (ou use --list)")
    publish(args.slug, status=args.status, dry_run=args.dry_run,
            emit_json=args.emit_json, probe=args.probe, locale=args.locale, update_id=args.update)


if __name__ == "__main__":
    main()
