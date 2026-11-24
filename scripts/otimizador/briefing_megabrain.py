# -*- coding: utf-8 -*-
"""Briefing do ciclo quinzenal: cruza TODOS os dados do Mega Brain com o Search Console do otimizador
e ranqueia os artigos do blog por oportunidade.

Fontes (retrato do dia do Mega Brain, dados/ultimo.json):
  top3 (50 keywords: posição, página que o Google mostra, dona, rivais) · plano_top3 (ações aprovadas do ciclo)
  blog (28 dias por artigo) · otimizador (o que deu resultado antes/depois) (keywords a reforçar) · mkase (cases mais vistos, para links internos)
  recomendacoes e destaques · diario (entregas recentes).
Mais: o inventário e o Log do otimizador (idade e cooldown de 28 dias) e a seleção por baldes do ciclo
(otimizador/ciclos/<ciclo>.json), que o baldes.py grava antes deste script.

Grupo de comparação (24/11/2026): a cada bloco de 4 candidatos parecidos no ranking, 1 é
sorteado (semente = ciclo) para NÃO ser mexido, até 8 por ciclo. Artigo com ação aprovada no
plano nunca vai para o grupo. O grupo entra no Log com Balde "Controle" (descanso de 28 dias,
medido como os outros) e mostra quanto do ganho é da reescrita e quanto é do blog crescendo.

Saída: otimizador/ciclos/<ciclo>-megabrain.md (o que o agente lê) e .json; com
--registrar-controle (padrão), o grupo de comparação é gravado no Log e no Inventário.

Uso:
    python scripts/otimizador/briefing_megabrain.py [--ciclo 2026-S47] [--max 25] [--sem-registrar]
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baldes import CICLOS, INTERVALO_DIAS, IDADE_MIN_DIAS, carregar_inventario, ciclo_id, data_iso, otimizacoes_por_url  # noqa: E402
from google_api import SKILL_DIR  # noqa: E402

MEGA = Path(os.environ.get("MEGA_BRAIN_DIR") or SKILL_DIR.parent / "Mega_Brain")
PARADAS = set("para como com uma uns das dos que nas nos por sem mais sobre guia completo marcas marca "
              "ecommerce commerce blog artigo melhor".split())


def norm(s):
    return unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9]+", norm(s)) if len(t) > 2 and t not in PARADAS}


def sobrepoe(a, b, minimo=2):
    return len(tokens(a) & tokens(b)) >= minimo


def retrato():
    """Atualiza o clone do Mega Brain (só leitura) e devolve o retrato do dia."""
    if (MEGA / ".git").exists():
        subprocess.run(["git", "-C", str(MEGA), "pull", "--ff-only", "-q"], capture_output=True, timeout=120)
    arq = MEGA / "dados" / "ultimo.json"
    if not arq.exists():
        raise SystemExit(f"[X] sem retrato do Mega Brain em {arq} (defina MEGA_BRAIN_DIR)")
    d = json.loads(arq.read_text(encoding="utf-8"))
    atraso = (date.today() - date.fromisoformat(d["dia"])).days
    if atraso > 2:
        print(f"[!] retrato do Mega Brain de {d['dia']} ({atraso} dias): dados defasados", file=sys.stderr)
    return d


def peso_posicao(pos):
    if pos is None:
        return 0
    return 1.0 if pos <= 6 else 0.7 if pos <= 12 else 0.35 if pos <= 20 else 0.1


def aprendizado(oti):
    """Média de variação de impressões por balde nas otimizações já medidas (o que fazer mais)."""
    por = {}
    for e in oti.get("detalhe", {}).get("artigos", []):
        if e.get("nota") != "aguardando" and e.get("variacao_impressoes_pct") is not None:
            por.setdefault(e["balde"], []).append(e["variacao_impressoes_pct"])
    return {b: {"n": len(v), "media_pct": round(sum(v) / len(v))} for b, v in por.items()}


CONTROLE_MAX = 8
CONTROLE_BLOCO = 4


def separar_controle(itens, ciclo, maximo):
    """Divide o ranking em (tratados, controle, reserva) com sorteio estratificado."""
    rng = random.Random(ciclo)
    trat, ctl, bloco, resto = [], [], [], []
    for it in itens:
        if len(trat) + len(bloco) >= maximo:
            resto.append(it)
            continue
        if "plano" in it["contexto"] or len(ctl) >= CONTROLE_MAX:
            trat.append(it)
            continue
        bloco.append(it)
        if len(bloco) == CONTROLE_BLOCO:
            ctl.append(bloco.pop(rng.randrange(CONTROLE_BLOCO)))
            trat += bloco
            bloco = []
    trat += bloco
    trat.sort(key=lambda i: -i["pontos"])
    return trat, ctl, resto


def montar(d, ciclo, maximo):
    B = {b["id"]: b for b in d["bracos"]}
    kws = [{"grupo": "nucleo", "linha": "", "dona": "", **k} for k in (B["top3"].get("detalhe") or {}).get("keywords", [])]
    blog = {a["slug"]: a for a in (B["blog"].get("detalhe") or {}).get("artigos", [])}
    plano = d.get("plano_top3") or {}
    # desde 09/11/2026 as ações do otimizador ficam em `acoes_otimizador` (o plano Top 3 ficou só com o time);
    # retratos mais antigos ainda as trazem em plano_top3.acoes_keyword
    fonte_acoes = d.get("acoes_otimizador") or plano.get("acoes_keyword", [])
    acoes_plano = [a for a in fonte_acoes if a.get("quem") == "otimizador" and a.get("status") != "feito"]
    cases = sorted((B["mkase"].get("detalhe") or {}).get("mais_vistos", []), key=lambda c: -(c.get("views_28d") or 0))[:8]

    inv = carregar_inventario()
    try:
        from planilhas import Planilhas
        otim = otimizacoes_por_url(Planilhas().ler_log())
    except Exception as e:  # sem o Log não dá para garantir o cooldown: segue só com a regra de idade e avisa
        print(f"[!] sem o Log do otimizador ({e}); cooldown não verificado", file=sys.stderr)
        otim = {}
    hoje = date.today()
    sel_baldes = {}
    arq = CICLOS / f"{ciclo}.json"
    if arq.exists():
        for s in json.loads(arq.read_text(encoding="utf-8")).get("selecionados", []):
            sel_baldes[s["url"]] = s

    itens = []
    for art in inv:
        url, slug = art["Slug/URL"], art["Slug/URL"].rstrip("/").rsplit("/", 1)[-1]
        caminho = "/blog/" + slug
        pub, datas = data_iso(art["Data de publicação"]), otim.get(url, [])
        if (pub and (hoje - pub).days < IDADE_MIN_DIAS) or (datas and (hoje - max(datas)).days < INTERVALO_DIAS):
            continue
        pts, porque, ctx = 0.0, [], {}
        # 1) keywords do Top 3 (as 50): o Google mostra este artigo, ou ele é a dona
        ks = [k for k in kws if k.get("pagina_que_aparece") == caminho or (k.get("dona") or "") == caminho]
        for k in ks:
            if not k["posicao"]:
                pts += 8
                porque.append(f'dona de "{k["kw"]}" sem nenhuma impressão: o artigo precisa responder essa busca')
            elif k["posicao"] > 3:
                v = k["impressoes"] * peso_posicao(k["posicao"])
                pts += v
                porque.append(f'"{k["kw"]}" na posição {k["posicao"]} com {k["impressoes"]} impressões em 28 dias '
                              f'(grupo {k["grupo"]}, {k["paginas_disputando"]} páginas da mK disputam)')
        if ks:
            ctx["keywords"] = [{c: k[c] for c in ("kw", "grupo", "linha", "posicao", "impressoes", "posicao_anterior", "dona",
                                                  "pagina_que_aparece", "paginas_disputando", "buscas")} for k in ks]
        # 2) seleção por baldes do Search Console (Decadente, CTR Baixo, Quick Win, Renovação)
        if url in sel_baldes:
            pts += 150
            porque.append(f'balde {sel_baldes[url]["balde"]}: {sel_baldes[url]["motivo"]}')
            ctx["balde"] = {"balde": sel_baldes[url]["balde"], "sinais": sel_baldes[url].get("sinais", []),
                            "queries": sel_baldes[url].get("queries", [])[:6]}
        # 3) ações já aprovadas no plano do Top 3 para este artigo
        plan = [a for a in acoes_plano if slug in a["acao"] or caminho in a["acao"] or (a["kw"] in [k["kw"] for k in ks] and a["ciclo"] == ciclo.split("-")[-1])]
        if plan:
            # ação do ciclo atual (ou atrasada) pesa cheio; de ciclo futuro entra como contexto, com peso menor
            vencidas = [a for a in plan if a["ciclo"] <= ciclo.split("-")[-1]]
            pts += 200 if vencidas else 60
            porque.append(f"{len(plan)} ação(ões) já aprovada(s) no plano do Top 3"
                          + ("" if vencidas else " (de ciclo futuro)"))
            ctx["plano"] = [f'{a["ciclo"]}: {a["acao"]}' for a in plan]
        # 3b) recomendações de SEO do Mega Brain que citam este artigo pelo endereço
        recs = [r for r in d.get("recomendacoes", []) if r["area"] == "SEO" and slug in r["texto"]]
        if recs:
            pts += 50
            porque.append("o Mega Brain recomenda: " + "; ".join(r["titulo"] for r in recs[:2]))
            ctx["recomendacoes"] = [f'{r["titulo"]}: {r["texto"][:240]}' for r in recs[:3]]
        # 4) desempenho próprio (28 dias)
        b = blog.get(slug)
        if b:
            ctx["gsc_28d"] = {k: b[k] for k in ("impressoes", "cliques", "posicao", "impressoes_antes")}
            if b["impressoes_antes"] >= 80 and b["impressoes"] <= 0.6 * b["impressoes_antes"]:
                pts += 60
                porque.append(f'impressões caíram de {b["impressoes_antes"]} para {b["impressoes"]} em 28 dias')
            if 4 <= b["posicao"] <= 15:
                pts += min(b["impressoes"], 300) * 0.3
        if pts <= 0:
            continue
        ctx["links_internos"] = [c["url"] for c in cases if sobrepoe(c["titulo"], slug, 1)][:3]
        itens.append({"slug": slug, "id": art.get("ID Payload"), "titulo": art["Título"], "keyword": art["Keyword principal"],
                      "pontos": round(pts), "porque": porque, "contexto": ctx})
    itens.sort(key=lambda i: -i["pontos"])
    trat, ctl, resto = separar_controle(itens, ciclo, maximo)
    return {
        "ciclo": ciclo, "retrato_do_mega_brain": d["dia"], "escolhidos": trat, "controle": ctl, "reserva": resto[:8],
        "geral": {
            "aprendizado_otimizador": aprendizado(B["otimizador"]),
            "recomendacoes": [r for r in d.get("recomendacoes", []) if r["area"] in ("SEO", "Otimizador")][:14],
            "entregas_recentes": [e for e in d.get("diario", []) if e["data"] >= (hoje - timedelta(days=14)).isoformat()][:15],
            "cases_para_links": [{"titulo": c["titulo"], "url": c["url"], "views_28d": c["views_28d"]} for c in cases[:5]],
            "keywords_sem_pagina": [k["kw"] for k in kws if k["grupo"] == "ceo" and not k["impressoes"]],
        },
    }


def registrar_controle(ctl, ciclo):
    """Grava o grupo de comparação no Log (Balde Controle, data de hoje) e marca no Inventário
    como 'Em observação', o que também o protege dos links retroativos do artigo diário."""
    from planilhas import Planilhas
    plan, hoje = Planilhas(), date.today().isoformat()
    campos = {"Balde": "Controle", "Data da otimização": hoje,
              "O que foi feito": "GRUPO DE COMPARAÇÃO: não mexido de propósito (sorteio do ciclo)",
              "Diagnóstico": "controle do ciclo: mede o blog sem reescrita, nas mesmas janelas"}
    for a in ctl:
        url = "https://metakosmos.com.br/blog/" + a["slug"]
        if not plan.atualizar_log(url, ciclo, campos):
            plan.anexar_log([{"URL do artigo": url, "Ciclo": ciclo, **campos}])
        plan.atualizar_inventario(url, {"Status": "Em observação (grupo de comparação, não mexer)"})
    print(f"[OK] grupo de comparação gravado: {len(ctl)} artigo(s)", file=sys.stderr)


def para_md(r):
    L = [f"# Briefing do ciclo {r['ciclo']} (Mega Brain de {r['retrato_do_mega_brain']})", "",
         "Os artigos abaixo estão em ordem de oportunidade. Pegue os primeiros, na ordem, até o teto do ciclo. "
         "Cada um traz o motivo, as keywords que ele serve e o contexto do plano. Este ciclo é só SEO (Google).", ""]
    g = r["geral"]
    if g["aprendizado_otimizador"]:
        L += ["## O que já deu resultado (variação média de impressões por dia, depois da reescrita)"]
        L += [f"- {b}: {v['media_pct']:+d}% em {v['n']} artigo(s)" for b, v in g["aprendizado_otimizador"].items()]
        L += ["Faça mais do que subiu; onde o balde ficou fraco, o artigo é majoritariamente busca de marca ou já tem dona melhor.", ""]
    for i, a in enumerate(r["escolhidos"], 1):
        L += [f"## {i}. {a['slug']}  ({a['pontos']} pontos)", f"id Payload: {a['id']} · keyword: {a['keyword'] or '—'}", ""]
        L += [f"- {p}" for p in a["porque"]]
        c = a["contexto"]
        for k in c.get("keywords", []):
            buscas = "; ".join(f'"{b["q"]}" (pos {b["pos"]}, {b["impr"]} imp)' for b in k["buscas"][:3])
            L += [f"  - keyword **{k['kw']}**: Google mostra {k['pagina_que_aparece'] or 'nenhuma página'}; dona definida: {k['dona'] or 'a definir'}. Buscas: {buscas or 'sem dados'}"]
        for p in c.get("plano", []):
            L += [f"  - plano aprovado: {p}"]
        for p in c.get("recomendacoes", []):
            L += [f"  - Mega Brain: {p}"]
        if c.get("links_internos"):
            L += [f"  - cases para linkar: {', '.join(c['links_internos'])}"]
        L += [""]
    if r.get("controle"):
        L += ["## Grupo de comparação: NÃO MEXER neste ciclo",
              "Sorteados entre candidatos parecidos para medir o efeito real da reescrita. Não otimize, não use como "
              "reserva e não insira links neles. Já estão gravados no Log como Balde \"Controle\"."]
        L += [f"- {a['slug']} ({a['pontos']})" for a in r["controle"]] + [""]
    if r["reserva"]:
        L += ["## Reserva (se algum escolhido cair na auditoria ou no cooldown)"] + [f"- {a['slug']} ({a['pontos']})" for a in r["reserva"]] + [""]
    if g["keywords_sem_pagina"]:
        L += ["## Keywords do CEO que ainda não aparecem no Google (viram pauta do blog, não otimização)",
              ", ".join(g["keywords_sem_pagina"]), ""]
    L += ["## Recomendações do Mega Brain"] + [f"- [{x['area']} p{x['prioridade']}] {x['titulo']}: {x['texto'][:220]}" for x in g["recomendacoes"]]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ciclo", default=ciclo_id(date.today()))
    ap.add_argument("--max", type=int, default=25, help="teto de artigos do ciclo (era 6 até 24/11/2026)")
    ap.add_argument("--sem-registrar", action="store_true", help="não grava o grupo de comparação no Log")
    args = ap.parse_args()
    r = montar(retrato(), args.ciclo, args.max)
    if r["controle"] and not args.sem_registrar:
        registrar_controle(r["controle"], args.ciclo)
    CICLOS.mkdir(parents=True, exist_ok=True)
    (CICLOS / f"{args.ciclo}-megabrain.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    md = para_md(r)
    (CICLOS / f"{args.ciclo}-megabrain.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
