# -*- coding: utf-8 -*-
"""Gera o HTML do documento "Performance dos provadores nos clientes (uso interno)", que vira
um Google Doc. Lê otimizador/dados/drive_decks/*.json (extraídos das apresentações do Drive).

Uso:
    python scripts/otimizador/doc_performance_html.py     # imprime o HTML e salva em otimizador/performance-clientes.html
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import SKILL_DIR  # noqa: E402

PASTA = SKILL_DIR / "otimizador" / "dados" / "drive_decks"
SAIDA = SKILL_DIR / "otimizador" / "performance-clientes.html"
PRIO = [("prova", 0), ("conversão", 1), ("conversao", 1), ("adiç", 2), ("adic", 2), ("aprova", 3), ("diagnóstico", 3),
        ("ctr", 4), ("abertura", 5)]


def esc(s):
    return html.escape(str(s), quote=False)


def limpa(s, maximo):
    s = re.split(r"\s*[(;]", s or "")[0].strip(" ,.")
    if len(s) > maximo:
        s = s[:maximo].rsplit(" ", 1)[0]
    return s



ACENTOS = [("usuarias", "usuárias"), ("usuaria", "usuária"), ("Usuarias", "Usuárias"), ("Adicoes", "Adições"), ("adicoes", "adições"),
           ("adicao", "adição"), ("Adicao", "Adição"), ("Sessoes", "Sessões"), ("sessoes", "sessões"), ("Participacao", "Participação"),
           ("experiencia", "experiência"), ("versao", "versão"), ("unicas", "únicas"), ("recomendacao", "recomendação"),
           ("Conversao", "Conversão"), ("conversao", "conversão"), ("Aprovacao", "Aprovação"), ("virtuais", "virtuais")]

# períodos e estados que os relatórios descrevem de forma longa ou ambígua
PERIODO = {"17tcG8nxAm4JHQPdyDDSIAc0etRFWuoTJ0JPAWYNwuOs": "3D: 05/08 a 25/01 (sem ano no relatório)",
           "1jMtny3v7txbsDDAtaeLmXt2_tZln7QejgOHd_WLIs9k": "30/06 a 30/08/2026",
           "1Bc1qI0MniEpNbm1ZYKCPDMLd3VCtgLOX5VqcYqkiBCk": "03 a 23/09/2026",
           "14FapvsVhRXZEB09WdY_99CF65_Zpmy7Lq3Erw2u05Vs": "01/06 a 30/08/2026",
           "1DJTXbUKcAgftIGgq9532XtmaNKh_yWyjStfcts9QVlQ": "11/03 a 10/06/2026",
           "1hugeTjmdHsEoR3f2ZfnI64U_JE_TcroFcIJ-8N7UupI": "sem data no relatório",
           "1YP7tJrZzDd3qq5-MDZq4uTf9821bVHleirYVErexsS0": "01/08 a 27/09/2026 (uso)",
           "1tpPQUiPkcDgN_hrdUBE3QekzWDkPBXVU1s9ax2pAnJo": "01 a 11/06/2026 (parcial)",
           "1T66kJMyZyMW-vZPbUjTLth4Dj15la2cHWvIrxVEMuFE": "POC 28/07 a 16/08/2026",
           "14o8fCgFcPIkTa19B18dWYv3gbZO-L610Vx1K-dlR-tw": "POC 28/07 a 16/08/2026"}


# estado de cada relatório, definido à mão a partir da leitura dos agentes (as etiquetas automáticas erravam)
ESTADO = {"14o8fCgFcPIkTa19B18dWYv3gbZO-L610Vx1K-dlR-tw": "versão anterior",
          "1T66kJMyZyMW-vZPbUjTLth4Dj15la2cHWvIrxVEMuFE": "versão mais completa",
          "1h5eUevlc4Z1oYeREsssl6Uc4o-KxEu_aP35NzTRcbsI": "em revisão",
          "1fG-l8PtnTrRM-HBWmKfInr1Hs3Bh4GnX84AsAY9RKe8": "v1 (a v2 corrige erros)",
          "1g5YoQNLfHr5Ps3TO5YPUcPdOaYgY6K47fN4CBVKSwEE": "v2",
          "19WTltEJiKVRrXjfDClrnhvOtlpjCy50_oy-dJMsCXHg": "primeiros dados",
          "1epb7KFz-A-o_fdNJVBwPW0hkovhCLZPZVEHlUjVywsg": "relatório mensal",
          "1QYeZ1JvELpZUfkAil8G9CnFTCN3hOXLd_9UOMwZJGIk": "v2",
          "15ukGxFqhM52bC0Qjhd70oCupE9pYf3aeMKyCyQYorNU": "relatório de POC",
          "13aEiSl7VmUgxQfbwILXFeaYNOKxm_APEgYwVjWrtPB8": "período parcial (21 dias)",
          "1D4Gt9ApQtCv0x9R9hTWJ3oWMI_-XQXoDLaIDHVpkm4o": "valores estimados",
          "1gv6V7VbGQl-VwfPIF7Fd7qf-Y8XGJPwL3OJ3tb8c5o8": "versão mais nova",
          "18fbK9AYCRIxj2msVUQjvwPCwbcgdzmq5gKk4DbX0T08": "versão anterior (superada)",
          "1nnYQwiZEsqHNh3GDHWqO1duU7lzVFlokLr3kBLStuO8": "POC de 6 dias",
          "17tcG8nxAm4JHQPdyDDSIAc0etRFWuoTJ0JPAWYNwuOs": "resultados e roadmap",
          "1tpPQUiPkcDgN_hrdUBE3QekzWDkPBXVU1s9ax2pAnJo": "período parcial (11 dias)",
          "1IlXVJnS-PqcAhos9x6Ko5C_1bkCNHMK9bF9jZaZx-is": "leitura parcial",
          "1hPyUHYGHWYWzRRRMLQBmZySSTT1-v4S6Gn9kWE0o4yo": "final",
          "1DJTXbUKcAgftIGgq9532XtmaNKh_yWyjStfcts9QVlQ": "relatório executivo",
          "1jMtny3v7txbsDDAtaeLmXt2_tZln7QejgOHd_WLIs9k": "só last click",
          "1Bc1qI0MniEpNbm1ZYKCPDMLd3VCtgLOX5VqcYqkiBCk": "único com cohort do GA4",
          "14FapvsVhRXZEB09WdY_99CF65_Zpmy7Lq3Erw2u05Vs": "v1",
          "1YP7tJrZzDd3qq5-MDZq4uTf9821bVHleirYVErexsS0": "setembro parcial",
          "1hugeTjmdHsEoR3f2ZfnI64U_JE_TcroFcIJ-8N7UupI": "deck de resultados (2023-24)",
          "12F9MeBu8cFNPFN04jJL4OF_s1Y_7IqjeAY8Cy5Lmvp0": "relatório mensal"}


def acentua(s):
    for a, b in ACENTOS:
        s = s.replace(a, b)
    return s


def estado_de(status):
    s = (status or "").lower()
    if "anterior" in s:
        return "versão anterior"
    if "mais nova" in s or "mais recente" in s or "mais completa" in s or "mais atualizada" in s:
        return "versão mais recente"
    if "em revis" in s:
        return "em revisão"
    for k in ("v1", "v2"):
        if re.search(r"" + k + r"", s):
            return k
    if s.startswith("final"):
        return "final"
    if "poc" in s:
        return "relatório de POC"
    if "resultados" in s or "executivo" in s:
        return "relatório de resultados"
    return "sem marcação"


def peso(nome):
    n = nome.lower()
    return min([p for k, p in PRIO if k in n] or [9])


def linhas_tabela():
    out = []
    for arq in sorted(PASTA.glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        mets = [m for m in d.get("metricas", []) if m["sensibilidade"] == "publicavel_com_aprovacao"
                and m["tipo"] in ("uso", "conversao", "engajamento") and not m.get("observacao", "").lower().startswith("projet")]
        if not mets:
            continue
        mets.sort(key=lambda m: (peso(m["nome"]), m.get("slide") or 99))
        vistos, esc_m = set(), []
        for m in mets:
            if m["nome"] in vistos or "(slide" in m["nome"] or "(funil)" in m["nome"]:
                continue
            vistos.add(m["nome"])
            esc_m.append(f"{m['nome']}: {m['valor']}")
            if len(esc_m) == 3:
                break
        link = f"https://docs.google.com/presentation/d/{d['deck_id']}"
        periodo = PERIODO.get(d["deck_id"]) or limpa(d.get("periodo", ""), 30)
        out.append((d["cliente"], limpa(d.get("produto", ""), 20), periodo,
                    acentua(" · ".join(esc_m)), ESTADO.get(d["deck_id"]) or estado_de(d.get("status_deck", "")), link))
    return out


def main():
    linhas = linhas_tabela()
    tr = "\n".join(
        f'<tr><td><a href="{l}">{esc(c)}</a></td><td>{esc(p)}</td><td>{esc(per)}</td><td>{esc(n)}</td><td>{esc(e)}</td></tr>'
        for c, p, per, n, e, l in linhas)
    h = f"""<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,sans-serif;font-size:11pt;line-height:1.45}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #bbbbbb;padding:5px 7px;vertical-align:top;font-size:9.5pt}}
th{{background:#eeeeee;text-align:left}}
</style></head><body>
<h1>Performance dos provadores nos clientes (uso interno)</h1>
<p><i>Levantamento de {date.today():%d/%m/%Y} a partir das apresentações mensais de performance no Drive da mK ({len(linhas)} relatórios com números de uso).</i></p>
<p><b>Este documento é interno. Os números vêm de relatórios feitos para cada cliente e não estão aprovados para o blog nem para material público.</b> Valores em R$ (receita da marca, investimento, ROI, fee) ficam de fora de propósito.</p>

<h2>O que os relatórios mostram</h2>
<ul>
<li><b>Coliseu Joalheria (mK Fashion+):</b> 21.586 provas finalizadas em agosto/26 e 97,3% de aprovação. O mês teve promoção e mais 2.060 produtos no provador.</li>
<li><b>Mari Maria (mK Beauty):</b> 598.737 provas de 28/07 a 07/10, 19,4 provas por usuária e CTR do provador de 8,15%.</li>
<li><b>Shiseido (mK Beauty):</b> quem abriu o provador adicionou ao carrinho 20,55% dos itens vistos, contra 10,38% de quem não abriu (+98%), em 03 a 23/09.</li>
<li><b>Zerezes (mK Fashion+):</b> 5.741 provas em setembro. A conversão por sessão de quem concluiu a prova foi de 1,44%, contra 0,31% de quem não usou.</li>
<li><b>Deluxecor (mK Home):</b> conversão por sessão de 1,38% para quem concluiu a prova, contra 0,09% para quem não usou, e 1.662 provas em setembro.</li>
<li><b>Ótica Mori (mK Fashion+):</b> conversão por sessão de 0,53% contra 0,17% em setembro, com 95,7% de aprovação. A base é de 11 compras.</li>
<li><b>Osklen (mK 3D Shop):</b> 3.632 aberturas do visualizador 3D, 35% delas em AR, e 46.173 aberturas no Shop the Look. O próprio relatório chama as taxas de adição ao carrinho de baixas, com potencial de 3 a 5 vezes.</li>
</ul>

<h2>Cuidados antes de usar qualquer número</h2>
<ul>
<li><b>Não são testes A/B.</b> As comparações "usou x não usou o provador" juntam grupos diferentes: quem conclui a prova já tem mais intenção de compra. Servem para a conversa comercial, mas não provam que o provador causou a diferença.</li>
<li><b>Os relatórios mudam de versão.</b> A Mari Maria tem duas versões para o mesmo período, com 648.457 e 598.737 provas, e provas por usuária de 23,3 contra 19,4. Na Shiseido, o relatório de julho/agosto diz 38.313 provas, mas o gráfico do próprio relatório soma 38.593, que é o número do outro deck. A Lathref mudou a definição de CTR entre os meses.</li>
<li><b>Várias bases são pequenas.</b> Os POCs duram de 6 a 20 dias, e algumas conversões partem de 11 a 14 compras.</li>
<li><b>Há cenários projetados.</b> CNS, Lathref (julho/agosto) e LK Sneakers trazem ROI projetado ou estimado, e o relatório da Mari Maria marca o cenário projetado como "a validar". Nada disso entra neste documento.</li>
<li><b>Dados de cliente final</b> (como o depoimento de uma usuária no relatório da Coliseu) exigem autorização própria.</li>
</ul>

<h2>Números de uso por relatório</h2>
<p>Até três números por relatório, só de uso e conversão, sem valores em R$. Cada nome leva ao relatório original no Drive.</p>
<table>
<tr><th>Cliente</th><th>Produto</th><th>Período</th><th>Números de uso</th><th>Estado do relatório</th></tr>
{tr}
</table>

<h2>O que ficou sem leitura</h2>
<ul>
<li><b>Ótica Mori, março, abril e maio:</b> os slides são imagens e o texto não vem na leitura. Só a taxa de conclusão de maio (67,11%, contra 59,24% em abril) apareceu.</li>
<li><b>Gregory (março/26) e Shop2gether:</b> só capa e galeria de imagens, sem números.</li>
<li><b>Redley (TMW+):</b> os gráficos de ROI e de resultados acumulados são imagens.</li>
<li><b>Dakota (RAM):</b> o gráfico mensal veio embaralhado e precisa ser conferido no slide.</li>
</ul>
<p>Para recuperar esses, serve um PDF ou um print dos slides, ou os números vindos do próprio time.</p>

<h2>Como um número passa a poder ir para o blog</h2>
<ol>
<li>O cliente autoriza por escrito o uso do número e do nome da marca.</li>
<li>O número é conferido no relatório final e na fonte (GA4 ou o painel do provador).</li>
<li>Ele entra na base de números com a fonte e vira um mKase ou um dado citável.</li>
</ol>
<p>Enquanto isso, o auditor do blog avisa sempre que um artigo repetir um destes números.</p>
</body></html>"""
    SAIDA.write_text(h, encoding="utf-8")
    print(f"[OK] {SAIDA} ({len(h)} caracteres, {len(linhas)} linhas na tabela)")


if __name__ == "__main__":
    main()
