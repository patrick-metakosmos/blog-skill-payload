# -*- coding: utf-8 -*-
"""Mede o resultado das otimizações (etapa 1.1.2.1, primeiro passo de cada ciclo).

Para cada linha do Log já executada ('O que foi feito' preenchido) e ainda sem
'Resultado', compara janelas IGUAIS antes e depois da data da otimização:
    depois = do dia seguinte à otimização até o último dia com dado no GSC
    antes  = o mesmo número de dias imediatamente antes da otimização
(no máximo 28 dias). Janelas iguais tornam cliques e impressões comparáveis;
por isso os campos "antes" do Log são reescritos com a janela da medição.

Resultado (variação da métrica principal; ±15% é a faixa de "Estável"):
    métrica principal = cliques, se o artigo teve 10+ cliques na janela antes;
                        senão impressões (volume baixo demais para clique).
    Melhorou -> Manter | Estável -> Avaliar 2ª rodada | Piorou -> Investigar
Com menos de 10 dias de dado depois, a linha fica para a próxima medição.

Uso:
    python scripts/otimizador/medir.py            # mede e grava no Log
    python scripts/otimizador/medir.py --dry-run  # só mostra
"""
import argparse
import sys
from datetime import date, datetime, timedelta

from google.auth.exceptions import RefreshError

from coleta_gsc import ATRASO, por_pagina, propriedade
from google_api import sessao_gsc
from planilhas import Planilhas

MIN_DIAS = 10
MAX_DIAS = 28
FAIXA_ESTAVEL = 0.15
MIN_CLIQUES_METRICA = 10


def variacao(antes, depois):
    if antes == 0:
        return None if depois == 0 else 1.0
    return depois / antes - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plan = Planilhas()
    pendentes = [l for l in plan.ler_log()
                 if l.get("O que foi feito", "").strip() and not l.get("Resultado", "").strip()]
    if not pendentes:
        print("[OK] nada a medir")
        return

    s, env = sessao_gsc()
    try:
        site = propriedade(s, env)
    except RefreshError:
        # plano B (login do Patrick no GSC): o Workspace da mK expira o login em horas.
        # O rodar_medicao.ps1 reconhece o código 3, abre o login e tenta de novo.
        print("[X] login do Search Console expirou: refazer o login e rodar de novo")
        sys.exit(3)
    ultimo_dia = date.today() - timedelta(days=ATRASO)
    vazio = {"cliques": 0, "impressoes": 0, "ctr": 0.0, "posicao": 0.0}

    for l in pendentes:
        url, ciclo = l["URL do artigo"], l["Ciclo"]
        feito = datetime.strptime(l["Data da otimização"][:10], "%Y-%m-%d").date()
        dias = min(MAX_DIAS, (ultimo_dia - feito).days)
        if dias < MIN_DIAS:
            print(f"[..] {url.rsplit('/', 1)[-1]}: só {max(dias, 0)} dia(s) de dado depois; mede no próximo ciclo")
            continue
        ini_dep, fim_dep = feito + timedelta(days=1), feito + timedelta(days=dias)
        ini_ant, fim_ant = feito - timedelta(days=dias), feito - timedelta(days=1)
        a = por_pagina(s, site, ini_ant, fim_ant).get(url, vazio)
        d = por_pagina(s, site, ini_dep, fim_dep).get(url, vazio)

        metrica = "cliques" if a["cliques"] >= MIN_CLIQUES_METRICA else "impressoes"
        v = variacao(a[metrica], d[metrica])
        if v is None or abs(v) <= FAIXA_ESTAVEL:
            resultado, proximo = "Estável", "Avaliar 2ª rodada"
        elif v > 0:
            resultado, proximo = "Melhorou", "Manter"
        else:
            resultado, proximo = "Piorou", "Investigar (considerar reverter)"
        nota = (f"{resultado} (janelas de {dias} dias: {metrica} {a[metrica]} → {d[metrica]}"
                f"{'' if v is None else f', {v:+.0%}'}; posição {a['posicao']} → {d['posicao']})")
        print(f"[{resultado}] {url.rsplit('/', 1)[-1]}: {nota}")
        if args.dry_run:
            continue
        plan.atualizar_log(url, ciclo, {
            "Posição média (antes)": a["posicao"], "Cliques (antes)": a["cliques"],
            "CTR (antes)": a["ctr"], "Impressões (antes)": a["impressoes"],
            "Posição média (depois)": d["posicao"], "Cliques (depois)": d["cliques"],
            "CTR (depois)": d["ctr"], "Impressões (depois)": d["impressoes"],
            "Resultado": nota, "Próximo passo": proximo,
        })
    if not args.dry_run:
        print("[OK] Log atualizado")


if __name__ == "__main__":
    main()
