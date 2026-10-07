# -*- coding: utf-8 -*-
"""Inventário de Artigos (Planilha 1 do processo 1.1.2).

Lê todos os posts pt-BR do Payload e gera otimizador/inventario.csv com os
campos do processo. Keywords vêm do output/<slug>/metadados.md quando o artigo
foi gerado pela skill; artigos migrados do WP ficam com keyword em branco.
Colunas de Search Console/GA4 ficam vazias aqui: quem preenche é a coleta.

Uso:
    python scripts/otimizador/inventario.py
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import OUTPUT_DIR, SKILL_DIR, http, load_env, log, payload_login  # noqa: E402

SITE = "https://metakosmos.com.br"
DESTINO = SKILL_DIR / "otimizador" / "inventario.csv"
BACKLOG = SKILL_DIR / "Pautas e Palavras Cahve" / "backlog.csv"

COLUNAS = [
    "Título", "Slug/URL", "Data de publicação", "Última atualização",
    "Keyword principal", "Keywords secundárias", "Categoria",
    "Posição média atual", "Cliques (último período)", "Impressões (último período)",
    "CTR atual", "Status", "Total de otimizações", "Última otimização",
    # extras do otimizador (não estavam no semi-plano)
    "ID Payload", "Engajamento médio (s)", "Leads (GA4)", "Citado pelas IAs",
]


def buscar_posts(auth):
    posts, pagina = [], 1
    while True:
        url = (f"{auth['api']}/api/posts?locale=pt-BR&depth=1&limit=100&page={pagina}"
               "&where[_status][equals]=published&sort=-publishedAt")
        code, resp = http("GET", url, token=auth["token"], scheme=auth["scheme"])
        if code != 200:
            log(f"GET posts falhou (HTTP {code})", "err")
            sys.exit(1)
        posts += resp.get("docs", [])
        if not resp.get("hasNextPage"):
            return posts
        pagina += 1


def keywords_do_backlog():
    """slug -> keyword, a partir do backlog editorial (fonte principal)."""
    if not BACKLOG.exists():
        return {}
    with BACKLOG.open(encoding="utf-8-sig", newline="") as f:
        return {r["slug"].strip(): r["keyword"].strip()
                for r in csv.DictReader(f) if r.get("slug") and r.get("keyword")}


def keywords_do_metadados(slug):
    """O metadados.md mudou de formato ao longo do tempo: '**Keyword Principal:** x',
    '**Keyword-alvo:** `x`' e a versão em tabela '| **Keyword-alvo** | `x` |'."""
    md = OUTPUT_DIR / slug / "metadados.md"
    if not md.exists():
        return "", ""
    texto = md.read_text(encoding="utf-8")

    def campo(*rotulos):
        for rotulo in rotulos:
            m = re.search(rf"\*\*{rotulo}:?\*\*:?\s*\|?\s*`?([^`|\n]+)", texto, re.I)
            if m and m.group(1).strip():
                return m.group(1).strip()
        return ""

    return campo("Keyword Principal", "Keyword-alvo", "Keyword"), campo("Keywords Secundárias")


def data(iso):
    return (iso or "")[:10]


def main():
    auth = payload_login(load_env())
    posts = buscar_posts(auth)
    backlog = keywords_do_backlog()
    DESTINO.parent.mkdir(exist_ok=True)
    sem_kw = 0
    with DESTINO.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUNAS)
        for p in posts:
            slug = p.get("slug", "")
            kw_md, kws = keywords_do_metadados(slug)
            kw = backlog.get(slug) or kw_md
            sem_kw += not kw
            cats = ", ".join(c.get("title", "") for c in p.get("categories") or [] if isinstance(c, dict))
            w.writerow([
                p.get("title", ""), f"{SITE}/blog/{slug}", data(p.get("publishedAt")),
                data(p.get("updatedAt")), kw, kws, cats,
                "", "", "", "", "Ativo", 0, "",
                p.get("id", ""), "", "", "",
            ])
    log(f"{len(posts)} artigos publicados -> {DESTINO}", "ok")
    log(f"{sem_kw} sem keyword no metadados (migrados do WP ou fora de output/)", "warn" if sem_kw else "ok")


if __name__ == "__main__":
    main()
