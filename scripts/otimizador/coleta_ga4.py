# -*- coding: utf-8 -*-
"""Coleta do GA4 para os artigos do blog (sinal extra do diagnóstico).

Dois recortes nos mesmos 90 dias do Search Console:
- por página (pagePath): visualizações e engajamento médio por visualização,
  em segundos. Artigo com tráfego e leitura curta pede abertura/estrutura.
- por página de entrada (landingPage): sessões que começaram no artigo e quantas
  viraram lead. O formulário fica em outra página, então o lead é atribuído
  ao artigo por onde a pessoa entrou. Lead = evento-chave da mK (mkl_captura).

Saída: otimizador/dados/ga4_<AAAA-MM-DD>.json

Uso:
    python scripts/otimizador/coleta_ga4.py
"""
import json
from datetime import date, timedelta

from google_api import SKILL_DIR, checar, sessao

SITE = "https://metakosmos.com.br"
DIAS = 90
DESTINO = SKILL_DIR / "otimizador" / "dados"
FILTRO_BLOG = {"filter": {"fieldName": "{campo}",
                          "stringFilter": {"matchType": "BEGINS_WITH", "value": "/blog/"}}}


def relatorio(s, prop, dimensao, metricas, ini, fim):
    filtro = json.loads(json.dumps(FILTRO_BLOG).replace("{campo}", dimensao))
    linhas, offset = [], 0
    while True:
        corpo = {"dateRanges": [{"startDate": ini, "endDate": fim}],
                 "dimensions": [{"name": dimensao}],
                 "metrics": [{"name": m} for m in metricas],
                 "dimensionFilter": filtro, "limit": 10000, "offset": offset}
        r = checar(s.post(f"https://analyticsdata.googleapis.com/v1beta/{prop}:runReport", json=corpo),
                   f"GA4 runReport {dimensao}")
        lote = r.get("rows", [])
        linhas += lote
        offset += len(lote)
        if not lote or offset >= r.get("rowCount", 0):
            return linhas


def url(caminho):
    return SITE + caminho.split("?")[0].split("#")[0].rstrip("/")


def main():
    s, env = sessao()
    prop = env.get("GA4_PROPERTY")
    if not prop:
        raise SystemExit("[X] GA4_PROPERTY ausente no .env")
    fim = (date.today() - timedelta(days=1)).isoformat()
    ini = (date.today() - timedelta(days=DIAS)).isoformat()

    paginas = {}
    for r in relatorio(s, prop, "pagePath", ["screenPageViews", "userEngagementDuration"], ini, fim):
        p = paginas.setdefault(url(r["dimensionValues"][0]["value"]), {"views": 0, "engajamento_s": 0.0})
        p["views"] += int(r["metricValues"][0]["value"])
        p["engajamento_s"] += float(r["metricValues"][1]["value"])
    for p in paginas.values():
        p["engajamento_medio_s"] = round(p.pop("engajamento_s") / p["views"], 1) if p["views"] else 0.0

    entradas = {}
    for r in relatorio(s, prop, "landingPage", ["sessions", "keyEvents"], ini, fim):
        e = entradas.setdefault(url(r["dimensionValues"][0]["value"]), {"sessoes": 0, "leads": 0})
        e["sessoes"] += int(r["metricValues"][0]["value"])
        e["leads"] += int(float(r["metricValues"][1]["value"]))

    dados = {"propriedade": prop, "periodo": [ini, fim], "paginas": paginas, "entradas": entradas}
    DESTINO.mkdir(parents=True, exist_ok=True)
    arq = DESTINO / f"ga4_{date.today().isoformat()}.json"
    arq.write_text(json.dumps(dados, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {prop}: {len(paginas)} artigos com visualização, "
          f"{sum(e['leads'] for e in entradas.values())} leads vindos do blog -> {arq}")


if __name__ == "__main__":
    main()
