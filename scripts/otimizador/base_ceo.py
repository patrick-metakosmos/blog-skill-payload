# -*- coding: utf-8 -*-
"""Gera o documento "Base de números e preços do blog" (para a diretoria) a partir de
references/precos-aprovados.json e references/numeros-oficiais.json.

As linhas das tabelas são escritas à mão (linguagem de diretoria), mas cada uma declara as
chaves da base que ela cobre; o script falha se uma chave não existir, para o documento
nunca divergir do que o auditor usa.

Uso:
    python scripts/otimizador/base_ceo.py
Saída: otimizador/Base-de-numeros-e-precos-do-blog.md
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import SKILL_DIR  # noqa: E402

REF = SKILL_DIR / "references"
SAIDA = SKILL_DIR / "otimizador" / "Base-de-numeros-e-precos-do-blog.md"

precos = json.loads((REF / "precos-aprovados.json").read_text(encoding="utf-8"))
base = json.loads((REF / "numeros-oficiais.json").read_text(encoding="utf-8"))
chaves = {n["valor"] for n in base["numeros"]}

# (número como aparece no artigo, o que significa, fonte, chaves da base que a linha cobre)
CASES = [
    ("+2,7 milhões", "Chevrolet (GM): pessoas alcançadas na 1ª semana dos FOOH dos elétricos", "Estudo + mKase General Motors", ["2,7 milhões"]),
    ("+101% e +775%", "Chevrolet: engajamento e CTR frente a anúncios convencionais", "Estudo", ["101%", "775%"]),
    ("20 milhões", "Chevrolet: acessos aos carros nos sites (configuradores 3D)", "Estudo", ["20 milhões"]),
    ("23,3 milhões (14,8 mi só no FOOH)", "Bio Extratus: visualizações orgânicas da campanha", "Estudo + mKase Bio Extratus", ["23,3 milhões", "14,8 milhões"]),
    ("8 milhões e 70%", "L'Oréal Professionnel iNOA: visualizações; 70% das interações vieram de quem não segue a marca", "Estudo + mKase", ["8 milhões", "70%"]),
    ("4 milhões", "UFC (UFC 307): visualizações orgânicas", "Estudo + mKase UFC", ["4 milhões"]),
    ("10 milhões", "TV Globo (Três Graças): visualizações orgânicas no Instagram da Globo em 1 semana (o mKase soma 50 milhões contando todas as postagens)", "Estudo", ["10 milhões"]),
    ("1,1 milhão e 15 mil comentários", "Stanley: visualizações orgânicas e comentários", "Estudo", ["1,1 milhão", "15 mil"]),
    ("11 milhões", "Rider: visualizações do vídeo com IA", "mKase Rider", ["11 milhões"]),
    ("5,5 milhões", "Movida: visualizações do vídeo com IA", "mKase Movida", ["5,5 milhões"]),
    ("226 mil · 101 mil · 27 mil", "Visualizações dos vídeos com IA da Oba Hortifruti, da Copra e do Colégio Sigma", "mKases", ["226 mil", "101 mil", "27 mil"]),
    ("+54% de pedidos", "iFood no BBB 26 (campanha de outro estúdio, dado do iFood citado no estudo)", "Estudo", ["54%"]),
]
MERCADO = [
    ("52% e 39%", "Usam tecnologias imersivas para ver o produto sem ir à loja (52%) e para ganhar confiança na compra (39%)", "Estudo", ["52%", "39%"]),
    ("até +94%", "Conversão com experiências 3D/AR. A Shopify publicou 94% para conteúdo 3D, em 2022", "Estudo + Shopify", ["94%"]),
    ("até +315%", "Conversão com 3D/AR (dado de potencial no estudo). Citar com \"até\", sem amarrar a um produto", "Estudo", ["315%"]),
    ("até -61%", "Devoluções (potencial no estudo, a partir de um exemplo de marca de móveis)", "Estudo", ["-61%"]),
    ("ROI de 7x a 40x", "\"Em projetos da mK\". O estudo também traz \"ROI esperado de 10 a 40x\" como potencial", "Estudo", ["7x", "40x"]),
    ("61% e 71%", "61% preferem marcas com experiências digitais interativas; 71% comprariam com mais frequência se houvesse AR", "Estudo", ["61%", "71%"]),
    ("28x", "Lembrar da marca 28x mais, só no contexto de AR em loja. Não é dado de FOOH e o estudo não cita a Nielsen", "Estudo", ["28x"]),
    ("88% e 93%", "88% das empresas usam IA regularmente (McKinsey); 93% de marcas e agências dizem que a IA acelera o fluxo de trabalho (StackAdapt)", "Estudo", ["88%", "93%"]),
    ("20% a 35%", "Redução do CAC com mais eficiência de conversão e viralização orgânica", "Estudo", ["20%", "35%"]),
    ("30% a 50%", "Redução na produção de conteúdo visual com IA (casos de mercado do capítulo da HumanHuman)", "Estudo", ["30%", "50%"]),
    ("47,4%", "Penetração de AR/VR do Brasil na América Latina em 2025", "Estudo", ["47,4%"]),
]
faltando = [c for _, _, _, cs in CASES + MERCADO for c in cs if c not in chaves]
assert not faltando, f"chaves fora da base: {faltando}"


def tabela(linhas):
    out = ["| Número | O que significa | Fonte |", "|---|---|---|"]
    out += [f"| **{n}** | {d} | {f} |" for n, d, f, _ in linhas]
    return "\n".join(out)


prod = precos["produtos"]
linhas_precos = ["| Produto | Preço | Como escrever no blog |", "|---|---|---|"]
for nome, v in prod.items():
    linhas_precos.append(f"| **{nome}** | a partir de {v['a_partir_de']} {v['unidade']} | \"a partir de {v['a_partir_de']} {v['unidade']}\" |")

def anexo_mkases():
    arq = REF / "numeros-mkases.json"
    if not arq.exists():
        return ""
    cases = json.loads(arq.read_text(encoding="utf-8"))["cases"]
    linhas = ["| mKase | Números de destaque | Quando |", "|---|---|---|"]
    n_com = 0
    # número que aparece em 4+ cases é texto-padrão de página (28X, 3X, 94%...), não resultado do case
    freq = {}
    for c in cases:
        for v in {n["valor"].lstrip("+").lower() for n in c["numeros"]}:
            freq[v] = freq.get(v, 0) + 1
    padrao = {v for v, k in freq.items() if k >= 4}

    def nome(c):
        base = c["titulo"].replace(" — mKase", "").replace("|", "·")
        slug = c["slug"].replace("-", " ")
        return f"{base} ({slug})"

    for c in sorted(cases, key=lambda x: x["slug"]):
        destaque = []
        for n in c["numeros"]:
            v = n["valor"].lstrip("+")
            if n["tipo"] != "metrica" or v.lower() in padrao or n["frase"] != c["descricao"][:420]:
                continue
            if v not in destaque:
                destaque.append(v)
        if not destaque:
            destaque = [n["valor"].lstrip("+") for n in c["numeros"]
                        if n["tipo"] == "metrica" and n["valor"].lstrip("+").lower() not in padrao][:3]
            destaque = list(dict.fromkeys(destaque))
        if not destaque:
            continue
        n_com += 1
        linhas.append(f"| [{nome(c)}]({c['url']}) | {' · '.join(destaque[:5])} | {c['data'] or '-'} |")
    cab = f"## Anexo A. Números dos mKases do site"
    intro = (f"Coletados em {date.today():%d/%m/%Y} das páginas públicas ({len(cases)} mKases lidos, {n_com} com números de resultado; "
             f"os demais falam de prazo e escopo). Cada número tem a frase de origem em `references/numeros-mkases.json`.")
    return "\n\n".join([cab, intro, "\n".join(linhas)])


def limpa(s, maximo):
    """Corta no primeiro '(' ou ';' (detalhes do agente) e, se ainda passar do limite, na última palavra inteira."""
    s = re.split(r"\s*[(;]", s or "")[0].strip(" ,.")
    if len(s) > maximo:
        s = s[:maximo].rsplit(" ", 1)[0]
    return s


def anexo_drive():
    """Anexo B: performance dos provadores nos clientes (apresentações internas do Drive).
    Só números de uso/conversão sem R$; valores em R$, ROI e fee ficam de fora de propósito."""
    pasta = SKILL_DIR / "otimizador" / "dados" / "drive_decks"
    if not pasta.exists():
        return ""
    prio = [("prova", 0), ("conversão", 1), ("conversao", 1), ("adiç", 2), ("adic", 2), ("aprova", 3),
            ("diagnóstico", 3), ("ctr", 4), ("abertura", 5)]

    def peso(nome):
        n = nome.lower()
        return min([p for k, p in prio if k in n] or [9])

    linhas = ["| Cliente | Produto | Período | Números de uso (sem R$) | Estado do relatório |", "|---|---|---|---|---|"]
    n = 0
    for arq in sorted(pasta.glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        mets = [m for m in d.get("metricas", []) if m["sensibilidade"] == "publicavel_com_aprovacao"
                and m["tipo"] in ("uso", "conversao", "engajamento") and not m.get("observacao", "").lower().startswith("projet")]
        if not mets:
            continue
        mets.sort(key=lambda m: (peso(m["nome"]), m.get("slide") or 99))
        vistos, escolhidos = set(), []
        for m in mets:
            if m["nome"] in vistos:
                continue
            vistos.add(m["nome"])
            escolhidos.append(f"{m['nome']}: {m['valor']}")
            if len(escolhidos) == 4:
                break
        n += 1
        estado = limpa(d.get("status_deck", ""), 28) or "-"
        link = f"https://docs.google.com/presentation/d/{d['deck_id']}"
        periodo = limpa(d.get("periodo", ""), 30)
        linhas.append(f"| [{d['cliente']}]({link}) | {limpa(d.get('produto', ''), 20)} | {periodo} | "
                      + " · ".join(escolhidos) + f" | {estado} |")
    cab = "## Anexo B. Performance dos provadores nos clientes (USO INTERNO)"
    aviso = ("**Estes números vêm de apresentações internas de performance do Drive e NÃO estão aprovados para o blog.** "
             "Cada cliente precisa autorizar o uso, e os relatórios têm divergências de método entre versões e períodos: "
             "a Mari Maria, por exemplo, tem duas versões do relatório com 648.457 e 598.737 provas para o mesmo período. "
             "Valores em R$ (receita da marca, investimento, ROI, fee) ficam de fora deste anexo. "
             "O auditor avisa quando um artigo repetir qualquer um destes números.")
    return "\n\n".join([cab, aviso, "\n".join(linhas)]) if n else ""


ANEXO_A = anexo_mkases()
ANEXO_B = anexo_drive()

md = f"""# Base de números e preços do blog metaKosmos

*Atualizada em {date.today():%d/%m/%Y}. Mantida pelo otimizador do blog; o auditor automático confere cada artigo contra esta base antes de publicar.*

## O que é e como funciona

- **Todo número e todo preço dos artigos do blog saem desta base.** Número que não está aqui gera aviso, e preço fora da lista reprova o artigo.
- **Quando as fontes divergem, vale o estudo** *The State of Immersive & Agentic Commerce 2026*.
- **Link interno não leva mais UTM**: ele reiniciava a sessão no GA4 e apagava a origem real da visita. Só o link do formulário mantém UTM.
- Há **4 pontos que esperam decisão sua** (seção 4).

## 1. Preços "a partir de"

Definidos pelo Patrick em {date.today():%d/%m/%Y}.

{chr(10).join(linhas_precos)}

**Regras de uso:** o preço aparece sempre como "a partir de", nunca como valor isolado. Produto sem preço definido (mK Veels, MK3D Provador e os cases) não cita valor. Os 135 negócios ganhos no Zoho não foram usados para definir os pisos, porque o campo de valor não diz se é mensal, anual ou do projeto.

## 2. Números de cases

{tabela(CASES)}

## 3. Números de mercado e de potencial

Os números de potencial entram sempre com "até" ou "potencial".

{tabela(MERCADO)}

## 4. Para decisão do CEO

1. **"Garantimos no mínimo 50% mais CTR"** (artigo de FOOH, no ar hoje). Soa como garantia pública, e o estudo não traz esse número. Manter com base interna, achar fonte ou tirar?
2. **"Até 7x mais performance de mídia", "até 8x mais engajamento" e "até 3x mais intenção de compra"** (artigo de FOOH). São alegações comerciais antigas sem fonte. O estudo traz outros números para o mesmo tema: ROI de 7x a 40x em projetos da mK e +94% de intenção de compra com AR. Manter, trocar pelos do estudo ou tirar?
3. **Gartner, "100 milhões de consumidores comprando com AR".** A fonte original é de **abril de 2019, para 2020**. O estudo (linha 2271) apresenta como projeção para 2026. Os artigos já seguem a fonte original, que está linkada. O estudo precisa de correção.
4. **Autoproclamações sem fonte.** O texto usa "agência #1 de FOOH no Brasil" e "mais de 100 projetos e 100 milhões de visualizações". Nenhum dos dois está no estudo, e o Guia GEO/AEO recomenda evitar autoproclamação sem prova. Manter com prova interna ou reformular?

Além disso, a página do mKase da Stanley diz "15 mil curtidas" e o estudo diz "15 mil comentários". Vale o estudo, e a página precisa ser corrigida.

## 5. Como a base é mantida

- Cada número tem fonte (linha do estudo ou página do mKase) e status. Os de status pendente ou sem fonte geram aviso em qualquer artigo que os use.
- Para incluir um número novo, ele é conferido na fonte e registrado na base antes de ir ao ar.
- Arquivos: `references/numeros-oficiais.json`, `references/numeros-mkases.json` e `references/precos-aprovados.json`, na pasta da skill do blog.

{ANEXO_A}

{ANEXO_B}
"""
SAIDA.write_text(md, encoding="utf-8")
print(f"[OK] {SAIDA} ({len(md)} caracteres)")
