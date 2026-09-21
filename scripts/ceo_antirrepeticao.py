#!/usr/bin/env python3
"""
ceo_antirrepeticao.py — impede que o post diário do Ian vire molde.

POR QUE ISTO EXISTE
Nos 4 primeiros posts, a âncora da L'Oréal apareceu em 4 de 4; "nove em cada 10 marcas
dormindo", "minha aposta" e "me diz sem filtro" em 3 de 4; e 3 aberturas começavam com
"Vou ser direto contigo" ou "Vou falar uma coisa". Medindo a similaridade global
(trigramas, Jaccard) dava 0,014 a 0,091: baixíssima. Ou seja, **um filtro de "texto
parecido" não pegaria nada**. A repetição não está no texto inteiro, está nos tijolos:
mesma âncora, mesma convicção, mesma fórmula de abertura e de fechamento.

Daí o mecanismo: orçamento por tijolo. Cada frase-assinatura, convicção, âncora, abertura
e fechamento só pode voltar depois de N posts. O histórico fica em
`references/ceo-historico.json` (versionado, para sobreviver a troca de máquina).

Uso direto:
    python scripts/ceo_antirrepeticao.py --relatorio   # a lista de queimados de hoje
    python scripts/ceo_antirrepeticao.py --semear      # reconstrói o histórico de output/
"""
import argparse
import glob
import io
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HIST = SKILL / "references" / "ceo-historico.json"
MAX_HIST = 40

# Frases que já viraram bordão nos posts. Casadas no texto normalizado (sem acento).
# O id é o que aparece no relatório; o valor é a regex.
FRASES_ASSINATURA = {
    "ancora-loreal": r"l oreal",
    "ecommerce-3-por-cento": r"menos de 3|nao chegava a 3",
    "agua-limpa": r"agua (ainda |segue |esta |ta )*limpa",
    "nove-em-cada-dez": r"(nove|9) em cada 10",
    "87-das-marcas": r"87",
    "perguntas-de-categoria": r"(trocam|evoluiu|evoluem|mudam) de categoria",
    "minha-aposta": r"minha aposta",
    "me-diz-sem-filtro": r"me diz sem filtro",
    "vou-ser-direto": r"vou ser direto",
    "talvez-incomode": r"talvez incomode",
    "mercado-dormindo": r"dormindo",
    "nice-to-have": r"nice to have",
    "o-obvio-que-e-hoje": r"o obvio que",
    "poc-no-ar": r"poc no ar|poque no ar",
    "compra-fisica": r"compra fisica|loja fisica",
    "tres-segundos": r"3 segundos|tres segundos",
    "atencao-novo-petroleo": r"novo petroleo",
    "kodak-blockbuster": r"kodak|blockbuster",
    "curva-de-adocao": r"curva de adocao|early adopter",
    "from-good-to-woow": r"from good to woow|espalhar mais woow",
}

# Quantos posts um tijolo precisa esperar para voltar.
GAP_FRASE = 4        # frase-assinatura usada nos ultimos 4 posts esta queimada
GAP_ABERTURA = 8     # as 6 primeiras palavras nao podem repetir
GAP_ABERTURA_2 = 3   # nem as 2 primeiras ("Vou ser...", "Trabalhei 10...")
GAP_FECHAMENTO = 5   # as 5 primeiras palavras da ultima linha de texto
GAP_CONVICCAO = 4
GAP_ANCORA = 6
GAP_ESTRUTURA = 2


def normalizar(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"https?://\S+", " ", t)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def palavras(t):
    return normalizar(t).split()


def linhas_de_texto(corpo):
    return [l for l in corpo.split("\n")
            if l.strip() and not re.fullmatch(r"(\s*#\w+)+\s*", l)]


def abertura(corpo, n=6):
    return " ".join(palavras(corpo)[:n])


def fechamento(corpo, n=5):
    ls = linhas_de_texto(corpo)
    return " ".join(palavras(ls[-1])[:n]) if ls else ""


def frases_no_corpo(corpo):
    flat = normalizar(corpo)
    return sorted(k for k, rx in FRASES_ASSINATURA.items() if re.search(rx, flat))


def campo(header, *nomes):
    for n in nomes:
        v = (header or {}).get(n)
        if v:
            return v.strip()
    return ""


def carregar():
    if not HIST.exists():
        return []
    try:
        return json.loads(HIST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def gravar(hist):
    HIST.parent.mkdir(exist_ok=True)
    HIST.write_text(json.dumps(hist[-MAX_HIST:], ensure_ascii=False, indent=2), encoding="utf-8")


def extrair(corpo, header, slug, data=None):
    """Monta a entrada de histórico de um post."""
    return {
        "data": data or datetime.now().strftime("%Y-%m-%d"),
        "slug": slug,
        "abertura": abertura(corpo),
        "abertura_2": abertura(corpo, 2),
        "fechamento": fechamento(corpo),
        "frases": frases_no_corpo(corpo),
        "conviccao": campo(header, "convicção", "conviccao"),
        "ancora": campo(header, "âncora", "ancora"),
        "estrutura": campo(header, "estrutura"),
    }


def _ultimos(hist, n, chave):
    vals = []
    for e in hist[-n:]:
        v = e.get(chave)
        if isinstance(v, list):
            vals.extend(v)
        elif v:
            vals.append(v)
    return vals


def checar(corpo, header, slug="", hist=None):
    """Retorna (errors, warnings, entrada). Tudo bloqueador aqui é objetivo:
    tijolo repetido antes do prazo."""
    hist = carregar() if hist is None else hist
    hist = [e for e in hist if e.get("slug") != slug]   # re-rodar o mesmo slug nao se compara consigo
    e = extrair(corpo, header, slug)
    errors, warnings = [], []

    queimadas = set(_ultimos(hist, GAP_FRASE, "frases"))
    repetidas = [f for f in e["frases"] if f in queimadas]
    if repetidas:
        errors.append(
            "Frase-assinatura repetida antes do prazo: " + ", ".join(repetidas) +
            f". Cada uma so volta depois de {GAP_FRASE} posts. Rode "
            "'python scripts/ceo_antirrepeticao.py --relatorio' e escolha outro caminho."
        )

    if e["abertura"] and e["abertura"] in _ultimos(hist, GAP_ABERTURA, "abertura"):
        errors.append(f'Abertura repetida ("{e["abertura"]}...") nos ultimos {GAP_ABERTURA} posts.')
    if e["abertura_2"] and e["abertura_2"] in _ultimos(hist, GAP_ABERTURA_2, "abertura_2"):
        errors.append(
            f'O post abre com "{e["abertura_2"]}...", igual a um dos ultimos {GAP_ABERTURA_2}. '
            "Troque a forma de entrar no assunto, nao so as palavras seguintes."
        )
    if e["fechamento"] and e["fechamento"] in _ultimos(hist, GAP_FECHAMENTO, "fechamento"):
        errors.append(f'Fechamento repetido ("{e["fechamento"]}...") nos ultimos {GAP_FECHAMENTO} posts.')

    if not e["conviccao"]:
        errors.append('Falta o campo "**Convicção:**" no cabecalho (qual convicção do repertorio sustenta o post).')
    elif e["conviccao"] in _ultimos(hist, GAP_CONVICCAO, "conviccao"):
        errors.append(f'Convicção "{e["conviccao"]}" usada nos ultimos {GAP_CONVICCAO} posts. '
                      "O repertorio tem mais de 20: pegue outra.")
    if not e["estrutura"]:
        errors.append('Falta o campo "**Estrutura:**" no cabecalho (qual das estruturas de linkedin-ceo.md).')
    elif e["estrutura"] in _ultimos(hist, GAP_ESTRUTURA, "estrutura"):
        errors.append(f'Estrutura "{e["estrutura"]}" usada nos ultimos {GAP_ESTRUTURA} posts.')
    if e["ancora"] and e["ancora"] in _ultimos(hist, GAP_ANCORA, "ancora"):
        errors.append(f'Ancora "{e["ancora"]}" usada nos ultimos {GAP_ANCORA} posts. '
                      "Historia repetida cansa mais rapido que dado repetido.")

    # rede grossa, so aviso: similaridade global costuma ser baixa mesmo em post repetitivo
    novo = set(zip(palavras(corpo), palavras(corpo)[1:], palavras(corpo)[2:]))
    for ant in hist[-10:]:
        if not ant.get("trigramas"):
            continue
        A, B = novo, set(tuple(t) for t in ant["trigramas"])
        if A and B:
            j = len(A & B) / len(A | B)
            if j > 0.25:
                warnings.append(f"Similaridade de {j:.0%} com o post de {ant.get('data')} ({ant.get('slug')}).")
    return errors, warnings, e


def registrar(entrada, corpo=None):
    hist = carregar()
    hist = [x for x in hist if not (x.get("slug") == entrada.get("slug") and x.get("data") == entrada.get("data"))]
    if corpo:
        ws = palavras(corpo)
        entrada = dict(entrada, trigramas=[list(t) for t in set(zip(ws, ws[1:], ws[2:]))][:400])
    hist.append(entrada)
    gravar(hist)
    return len(hist)


def relatorio(hist=None):
    hist = carregar() if hist is None else hist
    if not hist:
        return "Historico vazio: nada queimado, primeiro post livre."
    out = [f"HISTORICO DO POST DO CEO ({len(hist)} posts registrados)", ""]
    out.append("QUEIMADO HOJE (nao pode aparecer):")
    q = sorted(set(_ultimos(hist, GAP_FRASE, "frases")))
    out.append("  frases:     " + (", ".join(q) if q else "(nenhuma)"))
    out.append("  conviccoes: " + (", ".join(sorted(set(_ultimos(hist, GAP_CONVICCAO, "conviccao")))) or "(nenhuma)"))
    out.append("  ancoras:    " + (", ".join(sorted(set(_ultimos(hist, GAP_ANCORA, "ancora")))) or "(nenhuma)"))
    out.append("  estruturas: " + (", ".join(sorted(set(_ultimos(hist, GAP_ESTRUTURA, "estrutura")))) or "(nenhuma)"))
    out.append("")
    out.append("ABERTURAS recentes (nao repetir a forma de entrar):")
    for e in hist[-GAP_ABERTURA:]:
        out.append(f"  {e.get('data')}  {e.get('abertura', '')}...")
    out.append("")
    out.append("FECHAMENTOS recentes:")
    for e in hist[-GAP_FECHAMENTO:]:
        out.append(f"  {e.get('data')}  {e.get('fechamento', '')}...")
    return "\n".join(out)


def semear():
    """Reconstrói o histórico a partir dos linkedin-ceo.md em output/, na ordem em que
    foram postados (marcador .linkedin-ceo-posted.json quando existe)."""
    sys.path.insert(0, str(SKILL / "scripts"))
    from linkedin_publish import parse_linkedin_md  # noqa: E402
    itens = []
    for p in glob.glob(str(SKILL / "output" / "*" / "linkedin-ceo.md")):
        caminho = Path(p)
        slug = caminho.parent.name
        marcador = caminho.parent / ".linkedin-ceo-posted.json"
        data = None
        if marcador.exists():
            try:
                data = json.loads(marcador.read_text(encoding="utf-8")).get("posted_at", "")[:10]
            except json.JSONDecodeError:
                pass
        data = data or datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%Y-%m-%d")
        header, corpo = parse_linkedin_md(caminho)
        itens.append((data, slug, header, corpo))
    itens.sort(key=lambda x: x[0])
    hist = []
    for data, slug, header, corpo in itens:
        e = extrair(corpo, header, slug, data=data)
        ws = palavras(corpo)
        e["trigramas"] = [list(t) for t in set(zip(ws, ws[1:], ws[2:]))][:400]
        hist.append(e)
    gravar(hist)
    return hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relatorio", action="store_true", help="lista o que esta queimado hoje")
    ap.add_argument("--semear", action="store_true", help="reconstroi o historico de output/")
    a = ap.parse_args()
    if a.semear:
        hist = semear()
        print(f"[OK] historico semeado com {len(hist)} posts -> {HIST}")
        for e in hist:
            print(f"  {e['data']}  {e['slug'][:40]:40s} frases: {', '.join(e['frases']) or '-'}")
        return 0
    print(relatorio())
    return 0


if __name__ == "__main__":
    sys.exit(main())
