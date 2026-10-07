# -*- coding: utf-8 -*-
"""Coleta do Search Console para os artigos do blog (etapas 1.1.2.1 e 1.1.2.2).

Puxa, por URL de artigo, cliques/impressões/CTR/posição em dois períodos de
90 dias (atual e anterior, para o balde Decadentes) e as principais buscas
de cada artigo (para o diagnóstico dos Quick Wins). O Search Console atrasa
uns 3 dias, então o período atual termina em hoje - 3.

Saída: otimizador/dados/gsc_<AAAA-MM-DD>.json

Uso:
    python scripts/otimizador/coleta_gsc.py
    python scripts/otimizador/coleta_gsc.py --sites      # só lista as propriedades visíveis
"""
import argparse
import json
import urllib.parse
from datetime import date, timedelta

from google_api import SKILL_DIR, checar, sessao_gsc

API = "https://www.googleapis.com/webmasters/v3"
DIAS = 90
JANELA_LOG = 28
ATRASO = 3
QUERIES_POR_ARTIGO = 25
DESTINO = SKILL_DIR / "otimizador" / "dados"


def propriedade(s, env):
    """Prefere a propriedade de domínio; aceita a de prefixo de URL."""
    if env.get("GSC_SITE"):
        return env["GSC_SITE"]
    sites = [x["siteUrl"] for x in checar(s.get(f"{API}/sites"), "sites.list").get("siteEntry", [])]
    for candidato in ("sc-domain:metakosmos.com.br", "https://metakosmos.com.br/", "https://www.metakosmos.com.br/"):
        if candidato in sites:
            return candidato
    raise SystemExit(f"[X] Nenhuma propriedade da metakosmos visível para o robô. Visíveis: {sites}")


def consultar(s, site, corpo):
    url = f"{API}/sites/{urllib.parse.quote(site, safe='')}/searchAnalytics/query"
    linhas, inicio = [], 0
    while True:
        corpo = dict(corpo, rowLimit=25000, startRow=inicio)
        lote = checar(s.post(url, json=corpo), "searchAnalytics.query").get("rows", [])
        linhas += lote
        if len(lote) < 25000:
            return linhas
        inicio += 25000


SITE = "https://metakosmos.com.br"


def url_base(url):
    """O Google mostra os links do sumário (#secao) junto do resultado principal
    e o Search Console conta cada um como página à parte."""
    return url.split("#")[0].split("?")[0]


def url_do_artigo(url):
    """No WordPress (até 06/2026) o artigo morava na raiz com o mesmo slug:
    /fooh-guia-completo/ virou /blog/fooh-guia-completo. Leva a URL antiga para
    a nova, para o balde Decadentes comparar o mesmo artigo. Páginas que não são
    artigo (ex.: /mk-fashion/) também são convertidas, mas somem ao cruzar com o
    Inventário."""
    base = url_base(url).replace("://www.", "://")
    if "/blog/" in base:
        return base.rstrip("/")
    caminho = base.split("://", 1)[-1].split("/", 1)[-1].strip("/")
    if caminho and "/" not in caminho:
        return f"{SITE}/blog/{caminho}"
    return None


def por_pagina(s, site, ini, fim):
    """Métricas por artigo, em dois passos.
    1. #fragmento: aparece na mesma busca que a URL principal, então somar as
       impressões contaria a mesma exibição várias vezes. Vale a impressão e a
       posição da URL principal; só os cliques dos fragmentos são somados.
    2. URL antiga do WP + URL nova /blog/: são exibições diferentes (antes e
       depois do redirecionamento), então soma tudo, com a posição ponderada
       pelas impressões."""
    corpo = {"startDate": ini.isoformat(), "endDate": fim.isoformat(), "dimensions": ["page"]}
    linhas = consultar(s, site, corpo)

    por_url = {}
    for r in sorted(linhas, key=lambda r: "#" in r["keys"][0] or "?" in r["keys"][0]):
        base = url_base(r["keys"][0])
        if base not in por_url:
            por_url[base] = {"cliques": r["clicks"], "impressoes": r["impressions"],
                             "posicao": r["position"]}
        else:
            por_url[base]["cliques"] += r["clicks"]

    saida = {}
    for url, m in por_url.items():
        artigo = url_do_artigo(url)
        if artigo is None:
            continue
        a = saida.setdefault(artigo, {"cliques": 0, "impressoes": 0, "_pos": 0.0})
        a["cliques"] += m["cliques"]
        a["impressoes"] += m["impressoes"]
        a["_pos"] += m["posicao"] * m["impressoes"]
    for v in saida.values():
        v["posicao"] = round(v.pop("_pos") / v["impressoes"], 1) if v["impressoes"] else 0.0
        v["ctr"] = round(v["cliques"] / v["impressoes"], 4) if v["impressoes"] else 0.0
    return saida


def queries_por_pagina(s, site, ini, fim):
    corpo = {"startDate": ini.isoformat(), "endDate": fim.isoformat(), "dimensions": ["page", "query"]}
    # o site inteiro entra (cases, produto, home): a checagem de canibalização
    # precisa saber se outra página da mK já ocupa a busca do artigo. Período
    # atual, então URL fora de /blog/ é página de verdade, não artigo antigo do
    # WP. Por (página, busca) vale a linha de maior impressão (os #fragmentos
    # repetem a mesma exibição) e somam-se os cliques das demais.
    agreg = {}
    for r in consultar(s, site, corpo):
        pagina, query = r["keys"]
        chave = (url_do_artigo(pagina) if "/blog/" in pagina else url_base(pagina).rstrip("/"), query)
        atual = agreg.get(chave)
        if atual is None or r["impressions"] > atual["impressoes"]:
            cliques = r["clicks"] + (atual["cliques"] if atual else 0)
            agreg[chave] = {"query": query, "cliques": cliques, "impressoes": r["impressions"],
                            "posicao": round(r["position"], 1)}
        else:
            atual["cliques"] += r["clicks"]
    saida = {}
    for (pagina, _), q in agreg.items():
        q["ctr"] = round(q["cliques"] / q["impressoes"], 4) if q["impressoes"] else 0.0
        saida.setdefault(pagina, []).append(q)
    for pagina in saida:
        saida[pagina].sort(key=lambda q: -q["impressoes"])
        saida[pagina] = saida[pagina][:QUERIES_POR_ARTIGO]
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", action="store_true")
    args = ap.parse_args()

    s, env = sessao_gsc()
    if args.sites:
        print(json.dumps(checar(s.get(f"{API}/sites"), "sites.list"), indent=2, ensure_ascii=False))
        return

    site = propriedade(s, env)
    fim = date.today() - timedelta(days=ATRASO)
    ini = fim - timedelta(days=DIAS - 1)
    fim_ant = ini - timedelta(days=1)
    ini_ant = fim_ant - timedelta(days=DIAS - 1)
    ini_28 = fim - timedelta(days=JANELA_LOG - 1)

    dados = {
        "site": site,
        "periodo_atual": [ini.isoformat(), fim.isoformat()],
        "periodo_anterior": [ini_ant.isoformat(), fim_ant.isoformat()],
        "periodo_28": [ini_28.isoformat(), fim.isoformat()],
        "atual": por_pagina(s, site, ini, fim),
        "anterior": por_pagina(s, site, ini_ant, fim_ant),
        # "antes" do Log: mesma janela de 28 dias que a medição do "depois"
        "ultimos_28": por_pagina(s, site, ini_28, fim),
        "queries": queries_por_pagina(s, site, ini, fim),
    }
    DESTINO.mkdir(parents=True, exist_ok=True)
    arq = DESTINO / f"gsc_{date.today().isoformat()}.json"
    arq.write_text(json.dumps(dados, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {site}: {len(dados['atual'])} URLs no período atual, "
          f"{len(dados['anterior'])} no anterior -> {arq}")


if __name__ == "__main__":
    main()
