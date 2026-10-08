# -*- coding: utf-8 -*-
"""Gera o painel do Otimizador do Blog (página para a diretoria).

Junta numa página só o que as outras etapas já produziram: as coletas
(GSC/GA4), o Log e o Inventário (planilhas), os ciclos e as pastas de trabalho
de cada otimização. Também puxa do Search Console a série semanal do blog
desde a migração para o Payload. Os dados entram embutidos no HTML (o painel
não acessa nada sozinho), então depois de cada ciclo ou medição é rodar de
novo e republicar.

Uso:
    python scripts/otimizador/painel.py
Saída: otimizador/painel/index.html + painel.css (a partir de painel_template.html e painel.css)
"""
import csv
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from coleta_gsc import ATRASO, API, propriedade
from google_api import SKILL_DIR, checar, sessao_gsc
from planilhas import ABA_INVENTARIO, Planilhas

import urllib.parse

DADOS = SKILL_DIR / "otimizador" / "dados"
TRABALHO = SKILL_DIR / "otimizador" / "trabalho"
CICLOS = SKILL_DIR / "otimizador" / "ciclos"
SAIDA = SKILL_DIR / "otimizador" / "painel" / "index.html"
MODELO = Path(__file__).with_name("painel_template.html")
INICIO_PAYLOAD = date(2026, 6, 22)  # 1ª segunda-feira depois da migração (19/06)


def ultimo(prefixo):
    return json.loads(sorted(DADOS.glob(f"{prefixo}_*.json"))[-1].read_text(encoding="utf-8"))


def serie_semanal(s, site):
    """Cliques e impressões do blog por semana (seg-dom) desde a migração.
    Consulta sem dimensão de página: o GSC conta cada exibição uma vez só."""
    fim = date.today() - timedelta(days=ATRASO)
    corpo = {"startDate": INICIO_PAYLOAD.isoformat(), "endDate": fim.isoformat(), "dimensions": ["date"],
             "dimensionFilterGroups": [{"filters": [
                 {"dimension": "page", "operator": "contains", "expression": "/blog/"}]}],
             "rowLimit": 25000}
    url = f"{API}/sites/{urllib.parse.quote(site, safe='')}/searchAnalytics/query"
    linhas = checar(s.post(url, json=corpo), "série semanal").get("rows", [])
    semanas = {}
    for r in linhas:
        d = date.fromisoformat(r["keys"][0])
        seg = d - timedelta(days=d.weekday())
        w = semanas.setdefault(seg, {"cliques": 0, "impressoes": 0, "dias": 0})
        w["cliques"] += r["clicks"]
        w["impressoes"] += r["impressions"]
        w["dias"] += 1
    # semana incompleta no fim fica de fora: compararia 3 dias com 7
    return [{"semana": k.isoformat(), **v} for k, v in sorted(semanas.items()) if v["dias"] == 7]


def auditar(arquivo):
    saida = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "audit_artigo.py"), str(arquivo)],
                           capture_output=True, text=True, encoding="utf-8",
                           env={"PYTHONIOENCODING": "utf-8", **__import__("os").environ}).stdout
    corpo = re.search(r"corpo \(sem FAQ\): (\d+)", saida)
    return {"falhas": len(re.findall(r"FALHA", saida)) + len(re.findall(r"fora de 60-90", saida)),
            "palavras": int(corpo.group(1)) if corpo else 0}


def titulo(arquivo):
    m = re.search(r"<h1>(.*?)</h1>", arquivo.read_text(encoding="utf-8"), re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def main():
    gsc, ga4 = ultimo("gsc"), ultimo("ga4")
    plan = Planilhas()
    log = plan.ler_log()
    _, inventario = plan._ler(plan.id_inv, ABA_INVENTARIO)
    s, env = sessao_gsc()
    semanas = serie_semanal(s, propriedade(s, env))

    urls = [r["Slug/URL"] for r in inventario]
    atual = {u: gsc["atual"][u] for u in urls if u in gsc["atual"]}
    anterior = {u: gsc["anterior"][u] for u in urls if u in gsc["anterior"]}

    def soma(d, k):
        return sum(v[k] for v in d.values())

    imp, cli = soma(atual, "impressoes"), soma(atual, "cliques")
    kpis = {
        "impressoes": imp, "impressoes_ant": soma(anterior, "impressoes"),
        "cliques": cli, "cliques_ant": soma(anterior, "cliques"),
        "ctr": cli / imp if imp else 0,
        "posicao": sum(v["posicao"] * v["impressoes"] for v in atual.values()) / imp if imp else 0,
        "artigos_no_google": len(atual), "artigos": len(urls),
        "leads_blog": sum(e["leads"] for e in ga4["entradas"].values()),
        "views_blog": sum(p["views"] for p in ga4["paginas"].values()),
        "periodo": gsc["periodo_atual"], "periodo_ant": gsc["periodo_anterior"],
    }

    ciclos = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CICLOS.glob("*.json"))]
    selecionados = {e["url"]: (c["ciclo"], e) for c in ciclos for e in c["selecionados"]}
    log_por_url = {(l["URL do artigo"], l["Ciclo"]): l for l in log}

    otimizados = []
    for url, (ciclo, sel) in selecionados.items():
        slug = url.rsplit("/", 1)[-1]
        pasta = TRABALHO / slug
        l = log_por_url.get((url, ciclo), {})
        if not (pasta / "aplicado.json").exists():
            continue
        antes, depois = auditar(pasta / "original.html"), auditar(pasta / "artigo.html")
        seo = json.loads((pasta / "seo.json").read_text(encoding="utf-8"))
        otimizados.append({
            "slug": slug, "url": url, "ciclo": ciclo, "balde": sel["balde"], "motivo": sel["motivo"],
            "titulo_antes": titulo(pasta / "original.html"), "titulo_depois": titulo(pasta / "artigo.html"),
            "meta_title": seo["metaTitle"],
            "data": l.get("Data da otimização", ""),
            "antes": {"posicao": sel["antes_28d"]["posicao"], "cliques": sel["antes_28d"]["cliques"],
                      "impressoes": sel["antes_28d"]["impressoes"], "ctr": sel["antes_28d"]["ctr"]},
            "gsc_90d": sel["gsc_90d"],
            "resultado": l.get("Resultado", ""), "proximo": l.get("Próximo passo", ""),
            "auditoria": {"antes": antes, "depois": depois},
            "buscas": [q["query"] for q in sel["queries"][:3]],
        })

    pontos = []
    for r in inventario:
        u = r["Slug/URL"]
        if u not in atual:
            continue
        st = r.get("Status", "")
        grupo = ("otimizado" if u in selecionados else
                 "descartado" if st.startswith("Quick Win descartado") else
                 "novo" if st.startswith("Novo") else "elegivel")
        pontos.append({"slug": u.rsplit("/", 1)[-1], "titulo": r["Título"], "grupo": grupo,
                       "posicao": atual[u]["posicao"], "impressoes": atual[u]["impressoes"],
                       "cliques": atual[u]["cliques"], "nota": st if grupo == "descartado" else ""})

    medicao = min((datetime.fromisoformat(o["data"]).date() + timedelta(days=15) for o in otimizados if o["data"]),
                  default=None)
    dados = {
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "kpis": kpis, "semanas": semanas, "otimizados": otimizados, "pontos": pontos,
        "ciclos": [{"ciclo": c["ciclo"], "data": c["data"], "n": len(c["selecionados"])} for c in ciclos],
        "medicao": medicao.isoformat() if medicao else None,
        "ga4": {u: {**ga4["paginas"].get(u, {}), **ga4["entradas"].get(u, {})}
                for u in (o["url"] for o in otimizados)},
    }
    html = MODELO.read_text(encoding="utf-8").replace(
        "__DADOS__", json.dumps(dados, ensure_ascii=False).replace("</", "<\\/"))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(html, encoding="utf-8")
    (SAIDA.parent / "painel.css").write_text(MODELO.with_name("painel.css").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[OK] {SAIDA} | {len(otimizados)} otimizados, {len(pontos)} artigos no mapa, {len(semanas)} semanas")


if __name__ == "__main__":
    main()
