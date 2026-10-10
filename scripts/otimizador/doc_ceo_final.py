# -*- coding: utf-8 -*-
"""Gera o HTML do documento único para o CEO: decisões no topo, referências em anexo.

Junta o que antes eram dois documentos (base de números e preços + performance dos clientes).
As tabelas de números e de performance saem dos JSON; o texto das decisões é escrito à mão.

Uso:
    python scripts/otimizador/doc_ceo_final.py    # salva otimizador/documento-ceo.html
"""
import html
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_publish import SKILL_DIR  # noqa: E402
from doc_performance_html import linhas_tabela  # noqa: E402

REF = SKILL_DIR / "references"
SAIDA = SKILL_DIR / "otimizador" / "documento-ceo.html"
CX = "&#9744;"  # ☐

# relatórios mais recentes de cada cliente (os demais são versões superadas ou períodos parciais)
MANTER = {"1T66kJMyZyMW-vZPbUjTLth4Dj15la2cHWvIrxVEMuFE", "1h5eUevlc4Z1oYeREsssl6Uc4o-KxEu_aP35NzTRcbsI",
          "1g5YoQNLfHr5Ps3TO5YPUcPdOaYgY6K47fN4CBVKSwEE", "1epb7KFz-A-o_fdNJVBwPW0hkovhCLZPZVEHlUjVywsg",
          "1QYeZ1JvELpZUfkAil8G9CnFTCN3hOXLd_9UOMwZJGIk", "13aEiSl7VmUgxQfbwILXFeaYNOKxm_APEgYwVjWrtPB8",
          "1D4Gt9ApQtCv0x9R9hTWJ3oWMI_-XQXoDLaIDHVpkm4o", "1gv6V7VbGQl-VwfPIF7Fd7qf-Y8XGJPwL3OJ3tb8c5o8",
          "1nnYQwiZEsqHNh3GDHWqO1duU7lzVFlokLr3kBLStuO8", "17tcG8nxAm4JHQPdyDDSIAc0etRFWuoTJ0JPAWYNwuOs",
          "1hPyUHYGHWYWzRRRMLQBmZySSTT1-v4S6Gn9kWE0o4yo", "1DJTXbUKcAgftIGgq9532XtmaNKh_yWyjStfcts9QVlQ",
          "1Bc1qI0MniEpNbm1ZYKCPDMLd3VCtgLOX5VqcYqkiBCk", "1YP7tJrZzDd3qq5-MDZq4uTf9821bVHleirYVErexsS0",
          "12F9MeBu8cFNPFN04jJL4OF_s1Y_7IqjeAY8Cy5Lmvp0",
          # lote de 10/10/2026: demais clientes de Beauty, Fashion+, AI Studio, Home e 3D
          "16sHevCkD4RyQzXdaHSkrZfxsnAcaVxw-u8KltcC5rgk", "1oGHkH-hI6uuBM5mT9nJxPesntfvrIW8GDLv9dE6-yuM",
          "1qbHPq5677juNIx3OvZRn-U4DlQ6_0UWFSydfndlnz5k", "1WVmJ4uqjL1BZ9PTCo5v6oKxqub15BLWjPShpVgzX8uQ",
          "1a0ON6I2j5utIpIDY_Nd3RMsVY4oUTxoEqLUgM1Vi-qs", "1mvheZ9jU2mKawSxtteZXv9RSi8eswdTDTKIABvJ9FJI",
          "1-xoKCH7BuDSw2BdJZ6yXVAGrmuveILKK6682oyNhf1k", "1QIO_SRW1rWpfZdeqJWcXwF5-M4HLFen0Rnm3-uocaRg",
          "1z9x_WCaMLw9Nrj1vlfAknBUp5Om2hFs4PBd9KlMbH7Q", "1fVblgHspE6NmKRsYa4OTJlfKv9YhtJk2uGW_zuYSePs",
          "1rmpu68YKhw206XV1D4Cqv9psgb7-2-09thuxhFsNw7o", "1xWg_0zsI1CWaIVulrPJQwypJ-yD_HD_G0BqJ-rSQiG4",
          "1HGXlC4XdS7tLgEl3Y1mRvzyY8BogfW4_ElhbJwjG-BI", "1aGdOG-dN6yJqoV5ugowXF1SF3Ps4T3Sc27EFrIn7tGA",
          "1bBZUZD8UYMWYn0fuebctHHffRwLRU4FIIUPnWd27Xgg", "10nfD7LZsJPr5nTekmBJGABw16nVYCKz_w4WvkTX968c",
          "1ouS2Vc_iNk-DD1qnri_KAaFIr2CEBT6UAD07HkP4mlw", "1CFQkdHvqg1adiYZVLKws7jXiNXjtZyNbh8Y7ZR-8j74",
          "1AY0kiKogJb9CnzZUrmzIrdlLnLeRUKhZj463NnqBPto", "1snlrdWA3YT388WhjRVphwUMIs3Tj8geJqLQ2L7ah_NE"}

# correções de texto no anexo C (cliente, produto, período, números, estado); a tabela automática trunca e erra rótulos
AJUSTE = {
    "16sHevCkD4RyQzXdaHSkrZfxsnAcaVxw-u8KltcC5rgk": {"c": "Época Cosméticos", "p": "Jan-Set/2025 contra Jan-Set/2026",
        "n": "Páginas com provador: 131 para 793 (+505%) · Taxa de abertura: 2,51% para 4,28% (+71%) · Conversão do checkout: 3,14% para 5,47% (+74%)", "e": "comparativo ano contra ano"},
    "1rmpu68YKhw206XV1D4Cqv9psgb7-2-09thuxhFsNw7o": {"c": "Marisa", "pr": "mK AI Studio", "p": "POC de 22/06 a 21/08/2026",
        "n": "Adição ao carrinho em 19 produtos: 3.172 para 7.249 (+128,5%) · Visualizações de página: 23.425 para 40.834 (+74,3%) · Vendas: 177 para 184 (+4,0%)", "e": "relatório de POC (antes e depois)"},
    "1AY0kiKogJb9CnzZUrmzIrdlLnLeRUKhZj463NnqBPto": {"n": "Provas com AR: 969 (+74,59% sobre setembro) · Aberturas: 502 (-10,83%) · Adições ao carrinho: 64", "p": "Outubro/2025", "e": "relatório mensal"},
    "1snlrdWA3YT388WhjRVphwUMIs3Tj8geJqLQ2L7ah_NE": {"e": "relatório mensal"},
    "1HGXlC4XdS7tLgEl3Y1mRvzyY8BogfW4_ElhbJwjG-BI": {"p": "Out/2025 a 31/01 (ano não impresso)",
        "n": "Aberturas: 803, com 228 adições ao carrinho (28%) · Envio ao carrinho: 0,23% para 1,44% (6,2x) · Engajamento: +160% (5min09s contra 1min59s)", "e": "recap"},
    "1aGdOG-dN6yJqoV5ugowXF1SF3Ps4T3Sc27EFrIn7tGA": {"p": "29/10 a 10/11 (ano não impresso)", "n": "Aberturas do 3D: 34 · Adições ao carrinho: 4 (11,8%) · Aberturas com AR: 10 (29,4%)"},
    "1bBZUZD8UYMWYn0fuebctHHffRwLRU4FIIUPnWd27Xgg": {"c": "Petrobras", "n": "Arquivo por cena: cerca de 7-8 MB (360) contra cerca de 100 MB (3D livre) · Carregamento: cerca de 2 s (360) · Compatibilidade mobile: total (360) contra parcial (3D)", "e": "estudo técnico, sem período"},
    "1oGHkH-hI6uuBM5mT9nJxPesntfvrIW8GDLv9dE6-yuM": {"p": "06/07 a 20/09/2026", "n": "Provas: 245.383 · Conversão por sessão: 2,96% (abriu) contra 0,87% (não abriu) · Adição ao carrinho: 48,86% contra 10,64%"},
    "1fVblgHspE6NmKRsYa4OTJlfKv9YhtJk2uGW_zuYSePs": {"p": "10/02 a 31/12/2025"},
    "1QIO_SRW1rWpfZdeqJWcXwF5-M4HLFen0Rnm3-uocaRg": {"p": "16/10/2025 a 27/01/2026"},
    "1z9x_WCaMLw9Nrj1vlfAknBUp5Om2hFs4PBd9KlMbH7Q": {"p": "Nov/2024 a Fev/2026"},
    "1xWg_0zsI1CWaIVulrPJQwypJ-yD_HD_G0BqJ-rSQiG4": {"p": "POC de 22/06 a 21/08/2026 (61 dias)", "n": "Provas finalizadas: 2.048 · Taxa de aprovação: 92,1% · Produtos ativos no Provador: 673"},
    "1WVmJ4uqjL1BZ9PTCo5v6oKxqub15BLWjPShpVgzX8uQ": {"c": "M.Boom (mesmo grupo da Karen Bachini)"},
}


def esc(s):
    return html.escape(str(s), quote=False)


def tabela(cab, linhas):
    th = "".join(f"<th>{c}</th>" for c in cab)
    tr = "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f"<table>\n<tr>{th}</tr>\n{tr}\n</table>"


def main():
    precos = json.loads((REF / "precos-aprovados.json").read_text(encoding="utf-8"))["produtos"]
    tab_precos = tabela(["Produto", "Preço no blog", "Você confirma?"],
                        [[f"<b>{esc(n)}</b>", f"a partir de {esc(v['a_partir_de'])} {esc(v['unidade'])}", f"{CX} Sim &nbsp; {CX} Ajustar para: ______"]
                         for n, v in precos.items()])

    alegacoes = tabela(["Frase no artigo de FOOH (no ar hoje)", "Por que pedimos sua decisão", "Decisão"], [
        ["<b>\"Garantimos no mínimo 50% mais CTR\"</b>", "Soa como garantia pública e não tem fonte no estudo. <i>Sugestão: reformular como meta ou tirar.</i>",
         f"{CX} Manter (prova interna: ______)<br>{CX} Reformular como potencial<br>{CX} Tirar"],
        ["<b>\"Até 7x mais performance de mídia\", \"até 8x mais engajamento\", \"até 3x mais intenção de compra\"</b>", "Alegações comerciais antigas, sem fonte. O estudo traz outros números para o mesmo tema (ROI de 7x a 40x em projetos da mK, +94% de intenção de compra com AR).",
         f"{CX} Manter<br>{CX} Trocar pelos números do estudo<br>{CX} Tirar"],
        ["<b>\"Agência #1 de FOOH no Brasil\"</b>", "Autoproclamação sem prova no estudo. O Guia GEO/AEO recomenda evitar.",
         f"{CX} Manter (prova: ______)<br>{CX} Reformular<br>{CX} Tirar"],
        ["<b>\"Mais de 100 projetos e mais de 100 milhões de visualizações\"</b>", "Aparece em vários artigos e não está no estudo. Se a conta existir (Zoho, relatórios), vale registrar a origem.",
         f"{CX} Manter (origem do número: ______)<br>{CX} Reformular"],
    ])

    correcoes = tabela(["Ponto", "O que encontramos", "Decisão"], [
        ["<b>Gartner: \"100 milhões de consumidores comprando com AR\"</b>", "A fonte original é de <b>abril de 2019, para 2020</b>. O estudo (linha 2271) apresenta como projeção para 2026. Os artigos já seguem a fonte original, que está linkada.",
         f"{CX} Corrigir o estudo<br>{CX} Trocar por dado atual"],
        ["<b>Stanley: \"15 mil\"</b>", "O estudo diz 15 mil <i>comentários</i>; a página do mKase diz 15 mil <i>curtidas</i>. Vale o estudo.",
         f"{CX} Corrigir a página do mKase"],
        ["<b>+315% de conversão e -61% de devoluções</b>", "No estudo são <i>resultados esperados</i> (potencial), mas artigos antigos os usam como fato. Passam a entrar sempre com \"até\".",
         f"{CX} De acordo<br>{CX} Ajustar: ______"],
    ])

    AUT = f"{CX} Sim &nbsp; {CX} Não &nbsp; {CX} Já autorizado"
    clientes = tabela(["Cliente (produto)", "Número que poderia virar case", "Cuidado", "Autoriza abordar?"], [
        # mK Beauty: o produto com mais dados
        ["<b>Época Cosméticos</b> (mK Beauty)", "Jan-Set/25 contra Jan-Set/26: páginas com provador de 131 para 793 (+505%), taxa de abertura de 2,51% para 4,28% (+71%) e conversão do checkout de 3,14% para 5,47% (+74%)", "É o único comparativo ano contra ano, o mais forte do portfólio. O relatório de 2025 do mesmo cliente admite que a receita é estimada e que o tracking de itens vendidos diverge.", AUT],
        ["<b>Mantecorp</b> (mK Beauty)", "245.383 provas em 06/07 a 20/09/26; conversão por sessão de 2,96% (abriu o provador) contra 0,87% (não abriu); adição ao carrinho de 48,86% contra 10,64%", "Comparação entre grupos, não teste A/B. A alta de 17,3% em agosto vem da queda de sessões, não de mais vendas.", AUT],
        ["<b>Boca Rosa</b> (mK Beauty e 3D)", "16,3 milhões de provas em 2025 e 4,1 milhões em jul-ago/26 (4,5 milhões no 2º trimestre)", "O ROI do 2º trimestre usa último clique e o do 3º usa coorte do GA4, então não dá para dizer que \"subiu\". Os números de volume não têm esse problema.", AUT],
        ["<b>Mascavo</b> (mK Beauty)", "4.581.019 provas de jan a mai/26; 37,6% das compras do site passaram pelo provador; conversão de checkout de 19,88% contra 17,86% da base", "A comparação junta quem usa com todos os usuários.", AUT],
        ["<b>Natura</b> (mK Beauty)", "Piloto de 26/02 a 02/05/26: +455 mil provas, +62 mil usuárias e conversão de 3,55% contra 2,83% das páginas cobertas", "É piloto, não contrato. Marca global, pode exigir aprovação extra.", AUT],
        ["<b>Mari Maria</b> (mK Beauty)", "598.737 provas de 28/07 a 07/10 e 19,4 provas por usuária", "Há duas versões do relatório (648.457 e 598.737 provas) e o ROI é projetado, \"a validar\". Validar antes de pedir.", AUT],
        ["<b>Shiseido</b> (mK Beauty)", "Adição ao carrinho de 20,55% de quem abriu o provador, contra 10,38% de quem não abriu", "Comparação entre grupos, não teste A/B. Marca global, o contrato pode exigir aprovação extra.", AUT],
        ["<b>Simple Organic</b> (Skin AI)", "16.295 diagnósticos de pele em 3,5 meses, 50,2% dos acessos viram diagnóstico, e devolução de 4,52% contra 5,19% do e-commerce geral (-13%)", "É o único resultado de devolução do portfólio. O recorte de devolução (89 dias) é maior que o de uso (58 dias) no relatório de setembro.", AUT],
        ["<b>Karen Bachini Beauty</b> (mK Beauty)", "125.116 provas no 1º semestre de 2026; provador responde por 44,64% da receita das páginas que o têm (só mobile)", "Os meses somam 125.124, não 125.116. O relatório não traz ROI.", AUT],
        # mK Fashion+, AI Studio, Home, 3D
        ["<b>Marisa</b> (mK Fashion+ e AI Studio)", "POC de 22/06 a 21/08/26: conversão por sessão de 1,18% contra 0,51% (+130,5%) e aprovação de 92,1%. Com AI Studio, adição ao carrinho de 3.172 para 7.249 (+128,5%) em 19 produtos", "Grande varejista. Comparação entre grupos no provador e antes/depois no AI Studio; as vendas dos 19 produtos subiram só 4%.", AUT],
        ["<b>Zerezes</b> (mK Fashion+)", "Agosto/26: conversão por sessão de 1,04% contra 0,39% (+167,7%) e aprovação de 95%. Setembro: 5.741 provas", "Comparação entre grupos, não teste A/B.", AUT],
        ["<b>Track &amp; Field</b> (mK Fashion+)", "POC de 27/08 a 16/09/26: conversão por sessão de 2,68% contra 1,15% (+133,0%)", "As tabelas de sessões e vendas do relatório não somam o total, e o clique no botão (0,42%) está bem abaixo do que o próprio deck cita como referência (10 a 15%).", AUT],
        ["<b>Dumond</b> (mK Fashion+)", "13/07 a 20/09/26: conversão por sessão de 1,66% contra 1,04% (+58,9%) e aprovação de 97,7%", "As adições ao carrinho aparecem como 4.306 e como 1.754 em slides diferentes.", AUT],
        ["<b>Vivara</b> (mK Fashion+)", "3.387 provas em 17 dias de POC (21/07 a 06/08/26)", "A aprovação de 90,9% e a taxa de conclusão de 34,6% não fecham com os números do próprio deck.", AUT],
        ["<b>Coliseu Joalheria</b> (mK Fashion+)", "21.586 provas em agosto/26 e 97,3% de aprovação", "Mês com promoção e mais 2.060 produtos no provador. A v1 do relatório tinha erros, a v2 corrige.", AUT],
        ["<b>Ótica Mori</b> (mK Fashion+)", "Conversão por sessão de 0,53% contra 0,17% e 95,7% de aprovação em setembro", "Base de apenas 11 compras. Os relatórios de março a maio são imagens e não foram lidos.", AUT],
        ["<b>Deluxecor</b> (mK Home)", "Conversão por sessão de 1,38% (concluiu a prova) contra 0,09% (não usou) e 1.662 provas em setembro", "É o único cliente de mK Home com dado. Comparação entre grupos, não teste A/B.", AUT],
        ["<b>Stellantis, RAM Dakota</b> (mK 3D)", "Adoção do AR de 7,5% em fevereiro para 67,8% no pico de julho/26", "É adoção de recurso, não venda. 94,2% do uso é em dias úteis.", AUT],
        ["<b>Osklen</b> (mK 3D Shop)", "3.632 aberturas do visualizador 3D, 35% delas em AR, e 46.173 aberturas no Shop the Look", "O próprio relatório chama as taxas de adição ao carrinho de baixas. Os mKases atuais da Osklen não trazem número.", AUT],
        ["<b>Toymania</b> (mK 3D)", "Outubro/25: taxa de envio ao carrinho de 0,23% para 1,44% (6,2x) e engajamento +160% (5min09s contra 1min59s)", "Base pequena (4 para 33 itens) e o ano do período não está impresso no deck.", AUT],
    ])

    # anexo A: números oficiais
    base = json.loads((REF / "numeros-oficiais.json").read_text(encoding="utf-8"))["numeros"]
    por = {n["valor"]: n for n in base}
    CASES = [("+2,7 milhões", "Chevrolet (GM): pessoas alcançadas na 1ª semana dos FOOH dos elétricos", "Estudo + mKase", ["2,7 milhões"]),
             ("+101% e +775%", "Chevrolet: engajamento e CTR frente a anúncios convencionais", "Estudo", ["101%", "775%"]),
             ("20 milhões", "Chevrolet: acessos aos carros nos sites (configuradores 3D)", "Estudo", ["20 milhões"]),
             ("23,3 milhões (14,8 mi só no FOOH)", "Bio Extratus: visualizações orgânicas da campanha", "Estudo + mKase", ["23,3 milhões", "14,8 milhões"]),
             ("8 milhões e 70%", "L'Oréal Professionnel iNOA: visualizações; 70% das interações de quem não segue a marca", "Estudo + mKase", ["8 milhões", "70%"]),
             ("4 milhões", "UFC (UFC 307): visualizações orgânicas", "Estudo + mKase", ["4 milhões"]),
             ("10 milhões", "TV Globo (Três Graças): visualizações orgânicas no Instagram da Globo em 1 semana", "Estudo", ["10 milhões"]),
             ("1,1 milhão e 15 mil comentários", "Stanley: visualizações orgânicas e comentários", "Estudo", ["1,1 milhão", "15 mil"]),
             ("11 milhões", "Rider: visualizações do vídeo com IA", "mKase", ["11 milhões"]),
             ("5,5 milhões", "Movida: visualizações do vídeo com IA", "mKase", ["5,5 milhões"]),
             ("226 mil · 101 mil · 27 mil", "Vídeos com IA da Oba Hortifruti, da Copra e do Colégio Sigma", "mKases", ["226 mil", "101 mil", "27 mil"]),
             ("+54% de pedidos", "iFood no BBB 26 (campanha de outro estúdio, dado citado no estudo)", "Estudo", ["54%"])]
    MERCADO = [("52% e 39%", "Usam tecnologias imersivas para ver o produto sem ir à loja (52%) e para ganhar confiança (39%)", "Estudo", ["52%", "39%"]),
               ("até +94%", "Conversão com experiências 3D/AR. A Shopify publicou 94% para conteúdo 3D, em 2022", "Estudo + Shopify", ["94%"]),
               ("até +315%", "Conversão com 3D/AR (potencial no estudo)", "Estudo", ["315%"]),
               ("até -61%", "Devoluções (potencial no estudo)", "Estudo", ["-61%"]),
               ("ROI de 7x a 40x", "\"Em projetos da mK\" (estudo, linha 2947)", "Estudo", ["7x", "40x"]),
               ("61% e 71%", "61% preferem marcas com experiências digitais interativas; 71% comprariam com mais frequência se houvesse AR", "Estudo", ["61%", "71%"]),
               ("28x", "Lembrar da marca 28x mais, só no contexto de AR em loja. Não é dado de FOOH", "Estudo", ["28x"]),
               ("88% e 93%", "88% das empresas usam IA regularmente (McKinsey); 93% de marcas e agências dizem que a IA acelera o trabalho (StackAdapt)", "Estudo", ["88%", "93%"]),
               ("20% a 35%", "Redução do CAC com mais eficiência de conversão e viralização orgânica", "Estudo", ["20%", "35%"]),
               ("30% a 50%", "Redução na produção de conteúdo visual com IA (casos de mercado)", "Estudo", ["30%", "50%"]),
               ("47,4%", "Penetração de AR/VR do Brasil na América Latina em 2025", "Estudo", ["47,4%"])]
    faltando = [c for _, _, _, cs in CASES + MERCADO for c in cs if c not in por]
    assert not faltando, f"chaves fora da base: {faltando}"
    cab_n = ["Número", "O que significa", "Fonte"]
    anexo_a = tabela(cab_n, [[f"<b>{esc(n)}</b>", esc(d), esc(f)] for n, d, f, _ in CASES])
    anexo_a2 = tabela(cab_n, [[f"<b>{esc(n)}</b>", esc(d), esc(f)] for n, d, f, _ in MERCADO])

    linhas = []
    for c, p, per, n, e, l in linhas_tabela():
        if not any(i in l for i in MANTER):
            continue
        aj = next((v for k, v in AJUSTE.items() if k in l), {})
        linhas.append((aj.get("c", c), aj.get("pr", p), aj.get("p", per), aj.get("n", n), aj.get("e", e), l))
    anexo_b = tabela(["Cliente", "Produto", "Período", "Números de uso (sem R$)", "Estado"],
                     [[f'<a href="{l}">{esc(c)}</a>', esc(p), esc(per), esc(n), esc(e)] for c, p, per, n, e, l in linhas])

    h = f"""<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,sans-serif;font-size:11pt;line-height:1.45}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #bbbbbb;padding:5px 7px;vertical-align:top;font-size:9.5pt}}
th{{background:#eeeeee;text-align:left}}
</style></head><body>
<h1>Blog metaKosmos: preços, números e dados de clientes para sua decisão</h1>
<p><i>Preparado pelo Patrick em {date.today():%d/%m/%Y}. Para: Ian Borges.</i></p>

<h2>Em resumo</h2>
<p>O otimizador do blog já reescreveu 5 artigos, e junto com ele criamos uma base única de números e preços, que o sistema confere antes de qualquer artigo ir ao ar. Para ela ficar completa, <b>precisamos de 4 respostas suas</b>, nesta ordem: preços "a partir de", alegações antigas sem fonte, correções no estudo e quais clientes podem ter dados usados. Basta marcar uma opção em cada linha e devolver este documento.</p>

<h2>1. Preços "a partir de" para o blog</h2>
<p>Os valores abaixo foram definidos pelo Patrick. O blog usa sempre a forma "a partir de", nunca um valor isolado, e só para estes produtos. Mantemos o mK Veels e o MK3D Provador sem preço. Nos 135 negócios ganhos do Zoho há contratos de R$ 2 mil a R$ 460 mil, e o campo de valor não diz se é mensal, anual ou do projeto, por isso os pisos foram definidos à parte.</p>
{tab_precos}

<h2>2. Alegações antigas sem fonte</h2>
<p>Estas frases estão no artigo de FOOH que está no ar. O estudo <i>The State of Immersive &amp; Agentic Commerce 2026</i> não as sustenta. Hoje o sistema só avisa; não removemos nada sem sua decisão.</p>
{alegacoes}

<h2>3. Correções no estudo e nos mKases</h2>
{correcoes}

<h2>4. Dados de clientes: quais podemos abordar</h2>
<p>Lemos 67 relatórios de performance no Drive, de todos os produtos. Esses números são <b>internos</b>: cada cliente precisa autorizar o uso, e nada disso foi publicado. Abaixo, os 20 clientes com os resultados mais citáveis, com o <b>mK Beauty primeiro</b>, porque é de longe o produto com mais dados (13 clientes com relatório). Valores em R$ (receita da marca, investimento, ROI, fee) ficam sempre de fora; vários relatórios trazem ROI alto e estão no Drive para quem precisar. Se você autorizar abordar o cliente, o Patrick pede a autorização por escrito, o número é conferido no relatório final e só então vira case.</p>
<p><b>Cobertura por produto:</b> mK Beauty e mK Fashion+ têm dado de sobra. mK Home tem um cliente (Deluxecor). mK 3D Shop tem poucos, e com taxas baixas. mK AI Studio só tem a Marisa. <b>mK Labs quase não tem dado de performance</b>: o único relatório é uma comparação técnica de formato para a Petrobras, sem período e sem resultado de campanha. A prova do Labs está nos mKases e no estudo (Anexo A), não nos relatórios.</p>
{clientes}
<p><b>Regra geral:</b> dados de cliente só vão ao blog com autorização por escrito. {CX} De acordo &nbsp; {CX} Ajustar: ______</p>
<p><b>Atenção:</b> as comparações "usou x não usou o provador" juntam grupos diferentes (quem conclui a prova já tem mais intenção de compra). Servem para a conversa comercial, mas não provam que o provador causou a diferença, e não devem ser vendidas publicamente como se provassem.</p>

<h2>5. Para sua ciência (já decidido pelo Patrick)</h2>
<ul>
<li><b>Sem revisão humana antes de publicar.</b> A auditoria automática é a única barreira, por isso nenhum item dela pode ser relevado.</li>
<li><b>Mínimo de 2.000 palavras</b> por artigo, mesmo que a pauta peça menos.</li>
<li><b>Concorrentes: sem nome.</b> Comparamos as vantagens dos nossos produtos com "as soluções do mercado". Páginas comparativas nomeadas ficam para quando houver cerca de 10 cases (comentário seu no Intelligence Hub).</li>
<li><b>Link interno sem UTM.</b> O UTM reiniciava a sessão no GA4 e apagava a origem real da visita. Só o link do formulário mantém UTM. Para medir qual artigo leva ao clique, será preciso um evento no GTM.</li>
<li><b>Em conflito entre fontes, vale o estudo.</b> A exceção é o Gartner, onde a fonte original contradiz o estudo.</li>
</ul>
<p>Alguma destas você quer rever? {CX} Não &nbsp; {CX} Sim: ______</p>

<h2>Anexo A. Números aprovados para uso (cases)</h2>
<p>Todos conferidos no estudo ou na página pública do mKase. Os 46 mKases do site com números estão na base completa, que fica na pasta da skill do blog.</p>
{anexo_a}

<h2>Anexo B. Números de mercado e de potencial</h2>
<p>Os números de potencial entram sempre com "até" ou "potencial".</p>
{anexo_a2}

<h2>Anexo C. Relatórios de performance por cliente (uso interno)</h2>
<p>Só o relatório mais recente de cada cliente, com até três números de uso e sem valores em R$. Cada nome leva ao relatório original no Drive. Os de março a maio da Ótica Mori e o do Shop2gether são imagens e não puderam ser lidos; o relatório de lançamento da Zerezes só tem títulos. Vários relatórios trazem inconsistências internas (marcadas na coluna Cuidado da seção 4), por isso nenhum número daqui vira público sem conferência.</p>
{anexo_b}
</body></html>"""
    SAIDA.write_text(h, encoding="utf-8")
    print(f"[OK] {SAIDA} ({len(h)} caracteres; {len(linhas)} relatórios no anexo C)")


if __name__ == "__main__":
    main()
