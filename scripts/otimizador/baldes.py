# -*- coding: utf-8 -*-
"""Seleção do ciclo quinzenal (etapas 1.1.2.2 e 1.1.2.3 do processo).

Cruza Inventário (Payload) + Search Console + GA4 + Log e separa até
3 Quick Wins, 2 Decadentes e 2 CTR Baixo. As cotas são TETO: com o volume
pequeno do blog, um balde sem candidato acima do mínimo fica com vaga sobrando,
em vez de otimizar artigo por causa de ruído.

Regras de elegibilidade (valem para todos os baldes):
- artigo com 90+ dias no ar (o Google ainda está acomodando os mais novos);
- nenhuma otimização nos últimos 28 dias (senão a medição do "depois" fica suja).

Ordem de atribuição quando um artigo cabe em mais de um balde:
Decadente > CTR Baixo > Quick Win (do diagnóstico mais específico ao mais amplo).

Saída: otimizador/ciclos/<ciclo>.json, e (sem --dry-run) o Inventário
reescrito + as linhas do ciclo anexadas ao Log.

Uso:
    python scripts/otimizador/baldes.py --dry-run   # só mostra a seleção
    python scripts/otimizador/baldes.py             # grava ciclo + planilhas
"""
import argparse
import csv
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from google_api import SKILL_DIR
from planilhas import Planilhas

DADOS = SKILL_DIR / "otimizador" / "dados"
CICLOS = SKILL_DIR / "otimizador" / "ciclos"
INVENTARIO = SKILL_DIR / "otimizador" / "inventario.csv"

COTAS = {"Quick Win": 3, "Decadente": 2, "CTR Baixo": 2}
IDADE_MIN_DIAS = 90
INTERVALO_DIAS = 28

# Quick Win: posição 5-20, ordenado por impressões
QW_POSICAO = (5.0, 20.0)
QW_MIN_IMPRESSOES = 200
# Decadente: queda > 30% nos cliques (90d vs 90d anteriores), com base mínima
DEC_QUEDA = 0.30
DEC_MIN_CLIQUES_ANTES = 10
# reserva quando o volume de cliques é baixo demais: queda forte de impressões
DEC_QUEDA_IMPRESSOES = 0.40
DEC_MIN_IMPRESSOES_ANTES = 500
# CTR Baixo: posição 1-5, CTR abaixo de 60% do esperado para a posição
CTR_POSICAO = (1.0, 5.0)
CTR_MIN_IMPRESSOES = 100
CTR_FRACAO_ESPERADO = 0.60
# referência do semi-plano (1=28%, 2=15%, 3=10%, 5=5%); 4 interpolado. É ponto
# de partida: depois de alguns ciclos, recalibrar com o CTR real do site.
CTR_ESPERADO = {1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05}

# canibalização: outro artigo da mK com pelo menos isso de impressões na mesma busca
CANIB_MIN_IMPRESSOES = 30
# busca pela marca não é disputa: é natural vários artigos aparecerem nela
TERMOS_MARCA = ("metakosmos", "meta kosmos", "mk labs", "mklabs")

# sinais do GA4 (entram no diagnóstico, não criam balde)
GA4_MIN_VIEWS = 30
GA4_LEITURA_CURTA_S = 20
GA4_MIN_SESSOES_SEM_LEAD = 30


def ultimo(prefixo):
    arqs = sorted(DADOS.glob(f"{prefixo}_*.json"))
    if not arqs:
        raise SystemExit(f"[X] Nenhuma coleta {prefixo} em {DADOS}. Rode coleta_{prefixo}.py antes.")
    return json.loads(arqs[-1].read_text(encoding="utf-8"))


def ctr_esperado(pos):
    if pos <= 1:
        return CTR_ESPERADO[1]
    if pos >= 5:
        return CTR_ESPERADO[5]
    a = int(pos)
    return CTR_ESPERADO[a] + (CTR_ESPERADO[a + 1] - CTR_ESPERADO[a]) * (pos - a)


def ciclo_id(d):
    ano, semana, _ = d.isocalendar()
    return f"{ano}-S{semana:02d}"


def data_iso(texto):
    try:
        return datetime.strptime(texto.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def status_url_antiga(url_blog):
    """Decadente pode ser só migração: se a URL antiga do WP dá 404 em vez de
    redirecionar, o problema é o redirecionamento, não o texto."""
    slug = url_blog.rstrip("/").rsplit("/", 1)[-1]
    antiga = f"https://metakosmos.com.br/{slug}/"

    class SemSeguir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    req = urllib.request.Request(antiga, method="HEAD", headers={"User-Agent": "otimizador-blog-mk"})
    try:
        urllib.request.build_opener(SemSeguir).open(req, timeout=20)
        return 200, antiga
    except urllib.error.HTTPError as e:
        return e.code, antiga
    except urllib.error.URLError:
        return 0, antiga


def carregar_inventario():
    with INVENTARIO.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def otimizacoes_por_url(log):
    """Só conta como otimização a linha do Log com 'O que foi feito' preenchido;
    linha só selecionada (ainda não executada) não bloqueia nem soma."""
    saida = {}
    for l in log:
        feito = data_iso(l.get("Data da otimização", ""))
        if l.get("O que foi feito", "").strip() and feito:
            saida.setdefault(l["URL do artigo"], []).append(feito)
    return saida


def selecionar(hoje, inventario, gsc, ga4, log):
    otim = otimizacoes_por_url(log)
    atual, anterior, queries = gsc["atual"], gsc["anterior"], gsc["queries"]
    elegiveis, motivos_fora = [], {}

    for art in inventario:
        url = art["Slug/URL"]
        pub = data_iso(art["Data de publicação"])
        datas = otim.get(url, [])
        if pub and (hoje - pub).days < IDADE_MIN_DIAS:
            motivos_fora[url] = f"Novo (< {IDADE_MIN_DIAS} dias)"
        elif datas and (hoje - max(datas)).days < INTERVALO_DIAS:
            motivos_fora[url] = f"Em observação (otimizado há < {INTERVALO_DIAS} dias)"
        elif url not in atual:
            motivos_fora[url] = "Sem impressões no Google"
        else:
            elegiveis.append(url)

    cands = {b: [] for b in COTAS}
    descartados = []
    for url in elegiveis:
        m, a = atual[url], anterior.get(url)

        # Decadente
        if a and a["cliques"] >= DEC_MIN_CLIQUES_ANTES and m["cliques"] < a["cliques"] * (1 - DEC_QUEDA):
            queda = 1 - m["cliques"] / a["cliques"]
            cands["Decadente"].append((queda, url, f"cliques caíram {queda:.0%} ({a['cliques']} → {m['cliques']})"))
        elif (a and a["impressoes"] >= DEC_MIN_IMPRESSOES_ANTES
              and m["impressoes"] < a["impressoes"] * (1 - DEC_QUEDA_IMPRESSOES)):
            queda = 1 - m["impressoes"] / a["impressoes"]
            # pesa menos que queda de cliques na ordenação
            cands["Decadente"].append((queda / 2, url,
                                       f"impressões caíram {queda:.0%} ({a['impressoes']} → {m['impressoes']}), "
                                       f"posição {a['posicao']} → {m['posicao']} (cliques baixos demais para medir)"))

        # CTR Baixo
        if CTR_POSICAO[0] <= m["posicao"] <= CTR_POSICAO[1] and m["impressoes"] >= CTR_MIN_IMPRESSOES:
            esperado = ctr_esperado(m["posicao"])
            if m["ctr"] < esperado * CTR_FRACAO_ESPERADO:
                perdidos = (esperado - m["ctr"]) * m["impressoes"]
                cands["CTR Baixo"].append((perdidos, url,
                                           f"CTR {m['ctr']:.1%} na posição {m['posicao']} "
                                           f"(esperado ~{esperado:.0%}); ~{perdidos:.0f} cliques deixados na mesa"))

        # Quick Win (só se a busca principal não for de outra página da mK)
        if QW_POSICAO[0] <= m["posicao"] <= QW_POSICAO[1] and m["impressoes"] >= QW_MIN_IMPRESSOES:
            dono = dono_da_busca(url, queries)
            if dono:
                q, outra, pos = dono
                descartados.append((url, f"Quick Win descartado: \"{q}\" já é de {caminho(outra)} "
                                         f"(posição {pos}); empurrar o artigo canibalizaria essa página"))
            else:
                cands["Quick Win"].append((m["impressoes"], url,
                                           f"{m['impressoes']} impressões na posição {m['posicao']} "
                                           f"(CTR {m['ctr']:.1%})"))

    escolhidos, usados = [], set()
    for balde in ("Decadente", "CTR Baixo", "Quick Win"):
        n = 0
        for _, url, motivo in sorted(cands[balde], key=lambda c: -c[0]):
            if n >= COTAS[balde]:
                break
            if url in usados:
                continue
            usados.add(url)
            n += 1
            escolhidos.append(montar(balde, url, motivo, gsc, ga4))
    for url, motivo in descartados:
        if url not in usados:
            motivos_fora[url] = motivo
    return escolhidos, motivos_fora


def caminho(url):
    return url.replace("https://metakosmos.com.br", "") or "/"


def rivais_da_busca(url, query, queries):
    """Outras páginas da mK (artigo, case, produto) com volume na mesma busca."""
    saida = []
    for u, lista in queries.items():
        if u == url:
            continue
        for x in lista:
            if x["query"] == query and x["impressoes"] >= CANIB_MIN_IMPRESSOES:
                saida.append((u, x["posicao"]))
    return saida


def canibalizacao(url, queries, top=5):
    """Buscas principais do artigo em que OUTRA página da mK também aparece com
    volume: as duas disputam a mesma vaga e o Google alterna entre elas."""
    rivais = []
    for q in queries.get(url, [])[:top]:
        if q["impressoes"] < CANIB_MIN_IMPRESSOES or any(m in q["query"] for m in TERMOS_MARCA):
            continue
        outros = rivais_da_busca(url, q["query"], queries)
        if outros:
            rivais.append((q["query"], outros))
    return rivais


def dono_da_busca(url, queries):
    """Se a busca de maior volume do artigo já tem outra página da mK em posição
    melhor, o volume do artigo é ilusão de oportunidade (ex.: o artigo da Boca
    Rosa atrás do case /mkases/boca-rosa). Devolve (busca, página, posição)."""
    lista = queries.get(url, [])
    if not lista or any(m in lista[0]["query"] for m in TERMOS_MARCA):
        return None
    top = lista[0]
    melhores = [(u, pos) for u, pos in rivais_da_busca(url, top["query"], queries) if pos < top["posicao"]]
    if not melhores:
        return None
    outra, pos = min(melhores, key=lambda r: r[1])
    return top["query"], outra, pos


def montar(balde, url, motivo, gsc, ga4):
    m28 = gsc["ultimos_28"].get(url, {"cliques": 0, "impressoes": 0, "ctr": 0.0, "posicao": 0.0})
    item = {
        "balde": balde, "url": url, "motivo": motivo,
        "gsc_90d": gsc["atual"][url], "gsc_90d_anterior": gsc["anterior"].get(url),
        "antes_28d": m28, "queries": gsc["queries"].get(url, [])[:10],
        "sinais": [],
    }
    pagina = ga4["paginas"].get(url)
    entrada = ga4["entradas"].get(url)
    if pagina and pagina["views"] >= GA4_MIN_VIEWS and pagina["engajamento_medio_s"] < GA4_LEITURA_CURTA_S:
        item["sinais"].append(f"leitura curta: {pagina['engajamento_medio_s']}s por visualização "
                              f"em {pagina['views']} views (revisar abertura e estrutura)")
    if entrada and entrada["sessoes"] >= GA4_MIN_SESSOES_SEM_LEAD and entrada["leads"] == 0:
        item["sinais"].append(f"sem lead: {entrada['sessoes']} sessões entraram pelo artigo e nenhuma "
                              "virou lead (revisar CTA)")
    rivais = canibalizacao(url, gsc["queries"])
    if rivais:
        item["sinais"].append("canibalização: " + "; ".join(
            f"\"{q}\" também traz {', '.join(f'{caminho(u)} (pos {pos})' for u, pos in outros)}"
            for q, outros in rivais))
    if balde == "Decadente":
        codigo, antiga = status_url_antiga(url)
        if codigo not in (301, 302, 307, 308):
            item["sinais"].append(f"URL antiga do WP ({antiga}) responde {codigo or 'sem resposta'} em vez de "
                                  "redirecionar: parte da queda pode ser migração, corrigir o redirect primeiro")
    return item


def diagnostico(item):
    partes = [item["motivo"]]
    if item["balde"] == "Quick Win" and item["queries"]:
        top = "; ".join(f"\"{q['query']}\" (pos {q['posicao']}, {q['impressoes']} imp)" for q in item["queries"][:3])
        partes.append(f"buscas principais: {top}")
    partes += item["sinais"]
    return ". ".join(partes)


def linhas_inventario(hoje, inventario, gsc, ga4, log, escolhidos, motivos_fora):
    otim = otimizacoes_por_url(log)
    selecionados = {e["url"] for e in escolhidos}
    saida = []
    for art in inventario:
        url = art["Slug/URL"]
        l = dict(art)
        m = gsc["atual"].get(url)
        if m:
            l.update({"Posição média atual": m["posicao"], "Cliques (último período)": m["cliques"],
                      "Impressões (último período)": m["impressoes"], "CTR atual": m["ctr"]})
        if not l["Keyword principal"] and gsc["queries"].get(url):
            l["Keyword principal"] = gsc["queries"][url][0]["query"] + " (GSC)"
        pagina, entrada = ga4["paginas"].get(url), ga4["entradas"].get(url)
        l["Engajamento médio (s)"] = pagina["engajamento_medio_s"] if pagina else ""
        l["Leads (GA4)"] = entrada["leads"] if entrada else ""
        datas = otim.get(url, [])
        l["Total de otimizações"] = len(datas)
        l["Última otimização"] = max(datas).isoformat() if datas else ""
        l["Status"] = ("Candidato a otimização" if url in selecionados
                       else motivos_fora.get(url, "Ativo"))
        for k in ("ID Payload", "Total de otimizações", "Leads (GA4)"):
            if str(l.get(k, "")).isdigit():
                l[k] = int(l[k])
        saida.append(l)
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="só mostra a seleção, sem gravar nada")
    args = ap.parse_args()

    hoje = date.today()
    gsc, ga4, inventario = ultimo("gsc"), ultimo("ga4"), carregar_inventario()
    plan = Planilhas()
    log = plan.ler_log()  # leitura vale também no dry-run: o intervalo de 28 dias vem daqui

    escolhidos, fora = selecionar(hoje, inventario, gsc, ga4, log)
    ciclo = ciclo_id(hoje)

    print(f"Ciclo {ciclo} | {len(inventario)} artigos | "
          f"{sum(1 for v in fora.values() if v.startswith('Novo'))} novos demais, "
          f"{sum(1 for v in fora.values() if v.startswith('Em observação'))} em observação, "
          f"{sum(1 for v in fora.values() if v.startswith('Sem'))} sem impressões")
    for balde in COTAS:
        sel = [e for e in escolhidos if e["balde"] == balde]
        print(f"\n[{balde}] {len(sel)}/{COTAS[balde]}")
        for e in sel:
            print(f"  - {e['url'].rsplit('/', 1)[-1]}\n      {diagnostico(e)}")

    descartes = {u: m for u, m in fora.items() if m.startswith("Quick Win descartado")}
    if descartes:
        print(f"\n[Descartados] {len(descartes)}")
        for u, m in descartes.items():
            print(f"  - {u.rsplit('/', 1)[-1]}\n      {m}")

    if args.dry_run:
        return

    CICLOS.mkdir(parents=True, exist_ok=True)
    arq = CICLOS / f"{ciclo}.json"
    arq.write_text(json.dumps({"ciclo": ciclo, "data": hoje.isoformat(), "selecionados": escolhidos},
                              indent=1, ensure_ascii=False), encoding="utf-8")

    colunas = list(inventario[0].keys())
    removidas = plan.remover_pendentes(ciclo)
    plan.escrever_inventario(colunas, linhas_inventario(hoje, inventario, gsc, ga4, log, escolhidos, fora))
    novas = plan.anexar_log([{
        "URL do artigo": e["url"], "Ciclo": ciclo, "Balde": e["balde"],
        "Posição média (antes)": e["antes_28d"]["posicao"], "Cliques (antes)": e["antes_28d"]["cliques"],
        "CTR (antes)": e["antes_28d"]["ctr"], "Impressões (antes)": e["antes_28d"]["impressoes"],
        "Diagnóstico": diagnostico(e),
    } for e in escolhidos])
    print(f"\n[OK] {arq.name} gravado; Inventário atualizado; Log: {removidas} pendente(s) substituída(s), "
          f"{novas} linha(s) nova(s)")


if __name__ == "__main__":
    main()
