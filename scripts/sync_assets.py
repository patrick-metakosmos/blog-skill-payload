#!/usr/bin/env python3
"""
sync_assets.py — Sincronizador do banco de assets da skill blog-mk

Mantém references/assets-db.json atualizado com TODAS as mídias e links do WordPress,
preservando avaliações (score, best_use) já feitas. Regenera media-library.md e
blog-links.md como views legíveis a partir do banco.

O QUE FAZ (parte mecânica — pode rodar agendado):
  1. Autentica via JWT no metakosmos.com.br
  2. Puxa todas as mídias do WP (paginado)
  3. Puxa todos os posts publicados (com pilar inferido pela categoria)
  4. Puxa todos os mKases (custom post type ou páginas /mkases/)
  5. Faz diff com o banco: NOVOS, REMOVIDOS, links mortos (HTTP)
  6. Aplica heurística de categoria + score nas mídias novas (eval_method="heuristic")
  7. Preserva todas as avaliações visuais já feitas (eval_method="visual")
  8. Regenera media-library.md e blog-links.md
  9. Escreve sync-report.md com o resumo das mudanças

O QUE NÃO FAZ (precisa de mim, Claude, numa sessão):
  - Avaliação VISUAL das mídias (ver a imagem e dar nota). Mídias novas entram como
    "a avaliar"; rode evaluate_media.py para preparar os lotes.

Uso:
    python scripts/sync_assets.py                # sincroniza tudo
    python scripts/sync_assets.py --no-linkcheck # pula verificação de links mortos (mais rápido)
    python scripts/sync_assets.py --media-only   # só mídias
    python scripts/sync_assets.py --links-only   # só links
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REFS_DIR = SKILL_DIR / "references"
ENV_FILE = SKILL_DIR / ".env"
DB_FILE = REFS_DIR / "assets-db.json"
MEDIA_MD = REFS_DIR / "media-library.md"
LINKS_MD = REFS_DIR / "blog-links.md"
REPORT_MD = REFS_DIR / "sync-report.md"

USER_AGENT = "blog-mk-skill/1.0"

PILAR_BY_CATEGORY_SLUG = {
    "immersive-commerce": 1,
    "provador-virtual": 2,
    "visualizador-3d-ar": 3,
}


def log(msg, level="info"):
    print(f"{ {'info':'[i]','ok':'[OK]','warn':'[!]','err':'[X]'}.get(level,'[i]') } {msg}")


def load_env():
    env = {}
    if not ENV_FILE.exists():
        log(f".env nao encontrado em {ENV_FILE}", "err")
        sys.exit(1)
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def http(method, url, headers=None, body=None, jwt=None, timeout=60):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", USER_AGENT)
    headers.setdefault("Accept", "application/json")
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode("utf-8")
            return r.status, (json.loads(data) if data else {}), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8")), dict(e.headers)
        except Exception:
            return e.code, {}, {}
    except urllib.error.URLError as e:
        return 0, {"error": str(e)}, {}


def authenticate(env):
    log("Autenticando via JWT...")
    url = f"{env['WP_SITE_URL']}/?rest_route=/simple-jwt-login/v1/auth"
    body = urllib.parse.urlencode({
        "username": env["WP_USERNAME"], "password": env["WP_PASSWORD"]
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        jwt = d["data"]["jwt"]
        log(f"JWT obtido ({len(jwt)} chars)", "ok")
        return jwt
    except Exception as e:
        log(f"Erro de autenticacao: {e}", "err")
        sys.exit(1)


def fetch_paginated(env, jwt, endpoint, fields, extra=""):
    """Puxa todos os itens de um endpoint REST, paginado."""
    items = []
    page = 1
    while True:
        url = (f"{env['WP_SITE_URL']}/wp-json/wp/v2/{endpoint}"
               f"?per_page=100&page={page}&_fields={fields}{extra}")
        code, data, _ = http("GET", url, jwt=jwt)
        if code != 200 or not isinstance(data, list) or not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.2)
    return items


# === Heurística de mídia ===
def heuristic_media(m):
    slug = (m.get("slug") or "").lower()
    md = m.get("media_details") or {}
    w = md.get("width") or 0
    h = md.get("height") or 0
    mime = m.get("mime_type", "")
    date = (m.get("date") or "")[:10]

    blob = f"{slug} {(m.get('alt_text') or '').lower()}"

    if any(k in blob for k in ["selo", "logo", "partner", "cartela"]):
        cat = "logo"
    elif any(k in blob for k in ["depoimento", "stephanie", "guilherme", "elaine",
                                 "fernando", "monica", "celso", "hugo", "mariana", "daniela"]):
        cat = "depoimento"
    elif any(k in blob for k in ["dashboard", "metricas", "roi", "infografico", "grafico"]):
        cat = "infografico"
    elif any(k in blob for k in ["thumb", "capa", "hero", "cover"]):
        cat = "hero"
    elif mime == "image/gif" or "gif" in blob or "demo" in blob:
        cat = "gif_produto"
    else:
        cat = "inline"

    # Score heurístico 0-5 (provisório até avaliação visual)
    score = 3
    if w >= 1500:
        score += 1
    if w and w < 600:
        score -= 1
    if date >= "2026-01":
        score += 1
    if mime in ("image/svg+xml", "application/pdf"):
        score -= 2
    score = max(0, min(5, score))

    return cat, score


def detect_brand(slug):
    brand_map = {
        "flexform": "Flexform", "boca-rosa": "Boca Rosa", "toymania": "Toymania",
        "bio-extratus": "Bio Extratus", "bioextratus": "Bio Extratus", "loreal": "L'Oréal",
        "avon": "Avon", "natura": "Natura", "gm": "GM", "general-motors": "GM",
        "gregory": "Gregory", "osklen": "Osklen", "redley": "Redley", "mascavo": "Mascavo",
        "stanley": "Stanley", "heineken": "Heineken", "globo": "Globo", "fuel": "Fuel Eyewear",
        "epoca": "Época", "skala": "Skala", "anasol": "Anasol", "mili": "Mili", "copra": "Copra",
        "freeco": "Freeco", "aneethun": "Aneethun", "wap": "WAP", "oba": "Oba Hortifruti",
        "ilha-pura": "Ilha Pura",
    }
    s = (slug or "").lower()
    for k, v in brand_map.items():
        if k in s:
            return v
    return None


# === Heurística de link/post ===
def classify_post(post):
    cats = post.get("categories", [])
    slug = post.get("slug", "")
    title = (post.get("title") or {}).get("rendered", "")
    is_pillar = False
    # Pillar pages têm slug longo ou são marcadas — heurística simples
    if "guia-completo" in slug or "guia" in slug.split("-")[:2]:
        is_pillar = True
    return {
        "url": post.get("link", ""),
        "type": "pillar" if is_pillar else "article",
        "title": re.sub(r"&[a-z]+;", "", title),
        "slug": slug,
        "wp_id": post.get("id"),
        "categories": cats,
        "status": post.get("status", "publish"),
    }


def check_link(url, timeout=15):
    """HEAD request; retorna status HTTP ou 0 se falhar."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# === DB ===
def load_db():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    return {"meta": {}, "media": [], "links": []}


def save_db(db):
    DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Sincroniza banco de assets com o WordPress")
    ap.add_argument("--no-linkcheck", action="store_true", help="Pula verificação de links mortos")
    ap.add_argument("--media-only", action="store_true")
    ap.add_argument("--links-only", action="store_true")
    args = ap.parse_args()

    env = load_env()
    jwt = authenticate(env)
    db = load_db()

    # Index das avaliações existentes (preservar)
    media_by_id = {m["id"]: m for m in db.get("media", [])}
    links_by_url = {l["url"]: l for l in db.get("links", [])}

    report = [f"# Sync Report — {datetime.now(timezone.utc).isoformat()}\n"]
    new_media = new_links = dead_links = 0

    # === MÍDIAS ===
    if not args.links_only:
        log("Puxando mídias do WP...")
        wp_media = fetch_paginated(
            env, jwt, "media",
            "id,date,slug,source_url,mime_type,alt_text,media_details"
        )
        log(f"Mídias no WP: {len(wp_media)}", "ok")

        wp_media_ids = set()
        for m in wp_media:
            mid = m["id"]
            wp_media_ids.add(mid)
            md = m.get("media_details") or {}
            cat, score = heuristic_media(m)
            brand = detect_brand(m.get("slug", ""))
            if mid in media_by_id:
                # Preserva avaliação; só atualiza campos técnicos
                rec = media_by_id[mid]
                rec["url"] = m.get("source_url", rec.get("url"))
                rec["width"] = md.get("width", rec.get("width"))
                rec["height"] = md.get("height", rec.get("height"))
                rec["alt"] = m.get("alt_text", rec.get("alt"))
                if rec.get("eval_method") in (None, "none"):
                    rec["auto_category"], rec["score"] = cat, score
            else:
                media_by_id[mid] = {
                    "id": mid,
                    "url": m.get("source_url"),
                    "slug": m.get("slug"),
                    "mime": m.get("mime_type"),
                    "width": md.get("width"),
                    "height": md.get("height"),
                    "date": (m.get("date") or "")[:10],
                    "alt": m.get("alt_text", ""),
                    "brand": brand,
                    "auto_category": cat,
                    "use_category": None,
                    "theme_tags": [],
                    "score": score,
                    "best_use": "",
                    "eval_method": "none",   # none|heuristic|visual
                    "evaluated_at": None,
                }
                new_media += 1
        # Marca removidos
        for mid, rec in media_by_id.items():
            rec["in_wp"] = mid in wp_media_ids
        db["media"] = list(media_by_id.values())
        report.append(f"- Mídias no WP: **{len(wp_media)}**")
        report.append(f"- Mídias novas adicionadas: **{new_media}**")
        a_avaliar = sum(1 for m in db['media'] if m.get('eval_method') != 'visual')
        report.append(f"- Mídias a avaliar visualmente: **{a_avaliar}**")

    # === LINKS (posts + mKases) ===
    if not args.media_only:
        log("Puxando posts publicados...")
        posts = fetch_paginated(env, jwt, "posts",
                                "id,slug,link,title,categories,status",
                                extra="&status=publish")
        log(f"Posts publicados: {len(posts)}", "ok")

        # mKases e LPs são PÁGINAS (post type "page"), identificadas pela URL
        log("Puxando páginas (mKases ficam em /mkases/ e LPs em /mk-*/ )...")
        pages = fetch_paginated(env, jwt, "pages",
                                "id,slug,link,title,status", extra="&status=publish")
        log(f"Páginas publicadas: {len(pages)}", "ok")

        mkases, lps = [], []
        for pg in pages:
            link = pg.get("link") or ""
            if "/mkases/" in link:
                mkases.append(pg)
            elif re.search(r"/mk-[a-z0-9-]+/?$", link) or "/mklabs/" in link:
                lps.append(pg)
        log(f"mKases (páginas /mkases/): {len(mkases)} | LPs de produto: {len(lps)}", "ok")

        all_link_records = []
        for p in posts:
            all_link_records.append(classify_post(p))
        for mk in mkases:
            all_link_records.append({
                "url": mk.get("link", ""),
                "type": "mkase",
                "title": re.sub(r"&[a-z]+;", "", (mk.get("title") or {}).get("rendered", "")),
                "slug": mk.get("slug"),
                "wp_id": mk.get("id"),
                "categories": [],
                "status": mk.get("status", "publish"),
            })
        for lp in lps:
            all_link_records.append({
                "url": lp.get("link", ""),
                "type": "lp",
                "title": re.sub(r"&[a-z]+;", "", (lp.get("title") or {}).get("rendered", "")),
                "slug": lp.get("slug"),
                "wp_id": lp.get("id"),
                "categories": [],
                "status": lp.get("status", "publish"),
            })

        for rec in all_link_records:
            url = rec["url"]
            if not url:
                continue
            if url in links_by_url:
                links_by_url[url].update({
                    "title": rec["title"] or links_by_url[url].get("title"),
                    "type": rec["type"],
                    "status": rec["status"],
                })
            else:
                links_by_url[url] = {
                    "url": url,
                    "type": rec["type"],
                    "title": rec["title"],
                    "slug": rec.get("slug"),
                    "pilar": None,
                    "score": 5 if rec["type"] in ("pillar", "lp") else 4,
                    "best_use": "",
                    "status_http": None,
                    "last_checked": None,
                    "status": rec["status"],
                }
                new_links += 1

        # Verifica links mortos
        if not args.no_linkcheck:
            log("Verificando status HTTP dos links (pode demorar)...")
            for url, rec in links_by_url.items():
                st = check_link(url)
                rec["status_http"] = st
                rec["last_checked"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if st not in (200, 301, 302):
                    dead_links += 1
                time.sleep(0.1)

        db["links"] = list(links_by_url.values())
        report.append(f"- Posts publicados: **{len(posts)}**")
        report.append(f"- mKases (páginas): **{len(mkases)}**")
        report.append(f"- LPs de produto: **{len(lps)}**")
        report.append(f"- Links novos: **{new_links}**")
        report.append(f"- Links mortos (HTTP != 200/3xx): **{dead_links}**")
        if dead_links:
            report.append("\n### Links mortos detectados:")
            for rec in db["links"]:
                if rec.get("status_http") not in (200, 301, 302, None):
                    report.append(f"  - [{rec.get('status_http')}] {rec['url']}")

    # === Meta + salvar ===
    db["meta"] = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "total_media": len(db.get("media", [])),
        "total_links": len(db.get("links", [])),
        "media_evaluated_visual": sum(1 for m in db.get("media", []) if m.get("eval_method") == "visual"),
    }
    save_db(db)
    log(f"Banco salvo: {DB_FILE}", "ok")

    REPORT_MD.write_text("\n".join(report) + "\n", encoding="utf-8")
    log(f"Relatório salvo: {REPORT_MD}", "ok")

    print()
    log(f"RESUMO: {new_media} mídias novas | {new_links} links novos | {dead_links} links mortos", "ok")
    log("Para gerar os .md (views), rode: python scripts/render_views.py", "info")
    log("Para avaliar mídias novas visualmente, rode: python scripts/evaluate_media.py --prepare", "info")


if __name__ == "__main__":
    main()
