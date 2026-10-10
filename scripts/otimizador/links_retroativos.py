# -*- coding: utf-8 -*-
"""Links retroativos: depois de publicar um artigo novo, liga a Pillar Page do pilar e
2-3 artigos antigos do mesmo pilar a ele (UTMs §8.1/8.3 e Auditoria §3 "orphan pages").

Só insere o link onde o termo JÁ aparece em texto corrido, sem link, em parágrafo ou item
de lista (nunca em título, citação ou dentro de outro link). Onde não há ponto natural,
informa e não inventa frase. Link interno sem UTM (decisão de 10/2026).

A edição é no Lexical do próprio post (troca um nó de texto por texto + link + texto) e o
PATCH leva só o campo `content`: título, excerpt, SEO, capa, categoria e locales ficam como
estão. Antes de gravar, backup restaurável com `scripts/restore_post.py`.

Uso:
    python scripts/otimizador/links_retroativos.py <slug-novo> [--pilar N] [--max 3] [--ancora termo]  # só mostra
    python scripts/otimizador/links_retroativos.py <slug-novo> [--pilar N] [--max 3] --apply    # grava
"""
import argparse
import copy
import csv
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import (  # noqa: E402
    OUTPUT_DIR, SKILL_DIR, http, lex_link, lex_text, load_env, parse_metadados, payload_login)

BACKLOG = SKILL_DIR / "Pautas e Palavras Cahve" / "backlog.csv"
BACKUPS = SKILL_DIR / "backups"
SITE = "https://metakosmos.com.br"

# Pillar Page de cada pilar (references/pilares-conteudo.md). O script confere que existem.
PILLAR_PAGE = {
    1: "immersive-commerce-guia-completo-comercio-imersivo-lideres-ecommerce",
    2: "provador-virtual-ecommerce-guia-completo",
    3: "visualizador-3d-realidade-aumentada-ecommerce-guia",
    4: "fooh-guia-completo-fake-out-of-home-viral",
    5: "como-vender-mais-online",
    7: "futuro-do-varejo-digital",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def get_post(auth, slug):
    q = f"{auth['api']}/api/posts?where[slug][equals]={slug}&locale=pt-BR&depth=0&limit=1"
    code, r = http("GET", q, token=auth["token"], scheme=auth["scheme"])
    docs = r.get("docs") if isinstance(r, dict) else None
    return docs[0] if code == 200 and docs else None


def links_para(content, slug_alvo):
    achou = [False]

    def walk(n):
        if n.get("type") in ("link", "autolink") and slug_alvo in ((n.get("fields") or {}).get("url") or ""):
            achou[0] = True
        for c in n.get("children", []) or []:
            walk(c)
    walk(content["root"])
    return achou[0]


def inserir(content, ancoras, slug_alvo):
    """Troca o 1º nó de texto (em parágrafo/lista, fora de link) que contém uma âncora por
    texto + link + texto. Devolve (novo_content, trecho_antes, trecho_depois) ou None."""
    novo = copy.deepcopy(content)

    def passa(no, dentro_de_bloco_ok):
        tipo = no.get("type")
        if tipo in ("heading", "quote", "link", "autolink", "upload", "horizontalrule"):
            return None
        filhos = no.get("children") or []
        if tipo in ("paragraph", "listitem"):
            dentro_de_bloco_ok = True
        for i, f in enumerate(filhos):
            if f.get("type") == "text" and dentro_de_bloco_ok:
                txt = f.get("text", "")
                for a in ancoras:
                    # palavra inteira: "checkout" não casa com "checkouts"
                    m = re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", txt, re.I)
                    if m and f.get("format", 0) is not None:
                        pos = m.start()
                        antes, meio, depois = txt[:pos], txt[pos:m.end()], txt[m.end():]
                        fmt = f.get("format", 0)
                        pecas = []
                        if antes:
                            pecas.append(lex_text(antes, fmt))
                        pecas.append(lex_link(f"/blog/{slug_alvo}", [lex_text(meio, fmt)]))
                        if depois:
                            pecas.append(lex_text(depois, fmt))
                        filhos[i:i + 1] = pecas
                        no["children"] = filhos
                        return (antes[-60:], meio, depois[:60])
            else:
                r = passa(f, dentro_de_bloco_ok)
                if r:
                    return r
        return None

    r = passa(novo["root"], False)
    return (novo, r) if r else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--pilar", type=int)
    ap.add_argument("--max", type=int, default=3)
    ap.add_argument("--ancora", action="append", default=[],
                    help="variante extra de âncora (repetível), ex.: --ancora checkout. A keyword exata vem sempre primeiro")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    auth = payload_login(load_env())
    novo = get_post(auth, args.slug)
    if not novo:
        sys.exit(f"[X] artigo {args.slug} não encontrado no Payload")

    meta = OUTPUT_DIR / args.slug / "metadados.md"
    pilar = args.pilar or (parse_metadados(meta)["pilar"] if meta.exists() else None)
    if not pilar:
        sys.exit("[X] pilar desconhecido: passe --pilar N (1 a 7)")

    kw = novo["title"].split(":")[0].strip()
    ancoras = [kw]
    kw_curta = re.sub(r"\s*\(.*?\)", "", kw).strip()
    if kw_curta and kw_curta.lower() != kw.lower():
        ancoras.append(kw_curta)
    ancoras += [a for a in args.ancora if a.lower() not in [x.lower() for x in ancoras]]
    print(f"[i] artigo novo: {novo['title']}\n[i] pilar {pilar} | âncoras: {ancoras}")

    # hosts: Pillar Page + artigos do mesmo pilar (backlog), por cliques no GSC
    cliques = {}
    arqs = sorted((SKILL_DIR / "otimizador" / "dados").glob("gsc_*.json"))
    if arqs:
        for u, v in json.loads(arqs[-1].read_text(encoding="utf-8"))["atual"].items():
            cliques[u.rsplit("/", 1)[-1]] = v["cliques"]
    do_pilar = []
    if BACKLOG.exists():
        with BACKLOG.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("pilar", "").strip().upper() == f"P{pilar}" and r.get("slug") and r["status"] == "publicado":
                    do_pilar.append(r["slug"].strip())
    pagina = PILLAR_PAGE.get(pilar)
    ordem = ([pagina] if pagina else []) + sorted(
        [s for s in set(do_pilar) if s not in (pagina, args.slug)], key=lambda s: -cliques.get(s, 0))

    # não mexe em artigo em observação (medição de 28 dias)
    em_obs = set()
    try:
        from planilhas import Planilhas
        p = Planilhas()
        _, inv = p._ler(p.id_inv, "Inventário")
        em_obs = {r["Slug/URL"].rsplit("/", 1)[-1] for r in inv if r.get("Status", "").startswith("Em observ")}
    except Exception as e:  # noqa: BLE001
        print(f"[!] não consegui ler o Inventário no Drive ({e}); sem checar 'Em observação'")

    plano, sem_ponto, puladas = [], [], []
    for slug in ordem:
        if len(plano) >= args.max:
            break
        if slug in em_obs:
            puladas.append(f"{slug}: em observação (otimizado há < 28 dias)")
            continue
        host = get_post(auth, slug)
        if not host:
            puladas.append(f"{slug}: não está no Payload")
            continue
        if links_para(host["content"], args.slug):
            puladas.append(f"{slug}: já tem link para o artigo novo")
            continue
        r = inserir(host["content"], ancoras, args.slug)
        if r:
            plano.append((host, r[0], r[1]))
        else:
            sem_ponto.append(slug)

    print(f"\nPlano: {len(plano)} link(s)")
    for host, _, (a, m, d) in plano:
        print(f"  - {host['slug']} (post {host['id']}): ...{a}[[{m}]]{d}...")
    for s in sem_ponto:
        print(f"  . {s}: o termo não aparece em texto corrido (sem ponto natural; sugerir à mão)")
    for s in puladas:
        print(f"  . {s}")
    if not args.apply or not plano:
        if plano:
            print("\n(nada gravado: use --apply)")
        return

    for host, novo_content, _ in plano:
        nome = f"retroativo_{datetime.now():%Y%m%d_%H%M}_post{host['id']}"
        bdir = BACKUPS / nome
        bdir.mkdir(parents=True)
        (bdir / f"post_{host['id']}_pt-BR.json").write_text(json.dumps(host, ensure_ascii=False, indent=1), encoding="utf-8")
        (bdir / "manifest.json").write_text(json.dumps({"posts": [{"id": host["id"], "slug": host["slug"],
                                            "locales": {"pt-BR": f"post_{host['id']}_pt-BR.json"}}]}, ensure_ascii=False), encoding="utf-8")
        code, resp = http("PATCH", f"{auth['api']}/api/posts/{host['id']}?locale=pt-BR",
                          body={"content": novo_content}, token=auth["token"], scheme=auth["scheme"])
        pagina_ok = "?"
        if code in (200, 201):
            try:
                pagina_ok = urllib.request.urlopen(f"{SITE}/blog/{host['slug']}", timeout=30).status
            except Exception as e:  # noqa: BLE001
                pagina_ok = str(e)
        print(f"  [{'OK' if code in (200, 201) else 'X'}] {host['slug']}: HTTP {code}, página {pagina_ok} "
              f"| reverter: python scripts/restore_post.py {nome} {host['id']}")


if __name__ == "__main__":
    main()
