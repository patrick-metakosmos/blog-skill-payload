# -*- coding: utf-8 -*-
"""Coleta os mKases do site (lista pelo sitemap) e extrai os números de cada um.

Os mKases são públicos, então os números deles entram na base com fonte e URL. Cada número
vem com a frase em que aparece, para ninguém usar fora de contexto.

Saída: references/numeros-mkases.json
    {"coletado_em", "cases": [{"url","slug","titulo","descricao","data","numeros":[{"valor","tipo","frase"}]}]}

Uso:
    python scripts/otimizador/coleta_mkases.py
"""
import html as htmllib
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import SKILL_DIR  # noqa: E402

SITE = "https://metakosmos.com.br"
SAIDA = SKILL_DIR / "references" / "numeros-mkases.json"
UA = {"User-Agent": "otimizador-blog-mk/1.0"}

# número com unidade; "R$" fica de fora de propósito (valor em reais é resultado de cliente, não preço)
NUM = re.compile(r"(?<![\w.,])(?:R\$\s?)?[+\-]?\d[\d.,]*\s?(?:%|x\b|X\b|vezes|milh[ãõ][eo]s?|\bmi\b|\bmil\b|\bk\b|bilh[ãõ][eo]s?)", re.I)
PRAZO = re.compile(r"(?<![\w.,])\d{1,3}\s?(?:dias|semanas|meses|horas)(?!\w)", re.I)  # prazo de entrega: fato de execução, não resultado
MONETARIO = re.compile(r"R\$\s?\d")


def baixar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def texto_visivel(h):
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", h, flags=re.S)
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def corpo_do_case(t):
    """Do breadcrumb 'mKases / ...' até o rodapé; tira menu e rodapé do site."""
    i = t.find("mKases /")
    i = i if i >= 0 else 0
    corpo = t[i:]
    for fim in ("Precisa de um parceiro", "Quer ver o seu case", "Fale com um especialista Solu", "Conheça a metaKosmos", "Mais cases"):
        j = corpo.find(fim, 200)
        if j > 0:
            corpo = corpo[:j]
    return corpo


def frases(texto):
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\"“])", texto) if f.strip()]


def main():
    sitemap = baixar(SITE + "/sitemap.xml")
    urls = sorted(set(re.findall(r"<loc>(https://metakosmos\.com\.br/mkases/[^<]+)</loc>", sitemap)))
    print(f"[i] {len(urls)} mKases no sitemap")
    cases, falhas = [], []
    for u in urls:
        try:
            h = baixar(u)
        except Exception as e:  # noqa: BLE001
            falhas.append((u, str(e)))
            continue
        titulo = re.search(r"<title>(.*?)</title>", h, re.S)
        titulo = htmllib.unescape(titulo.group(1)).split(" | ")[0].strip() if titulo else ""
        desc = re.search(r'<meta name="description" content="(.*?)"', h)
        desc = htmllib.unescape(desc.group(1)) if desc else ""
        corpo = corpo_do_case(texto_visivel(h))
        nums, vistos = [], set()
        for fr in [desc] + frases(corpo):
            for m in list(NUM.finditer(fr)) + list(PRAZO.finditer(fr)):
                v = re.sub(r"\s+", " ", m.group(0)).strip()
                chave = (v.lower(), fr[:80])
                if chave in vistos:
                    continue
                vistos.add(chave)
                nums.append({"valor": v, "tipo": "monetario" if MONETARIO.match(v) else ("prazo" if PRAZO.fullmatch(v) else "metrica"), "frase": fr[:420]})
        data = re.search(r"(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+20\d\d", corpo, re.I)
        cases.append({"url": u, "slug": u.rsplit("/", 1)[-1], "titulo": titulo, "descricao": desc,
                      "data": data.group(0) if data else "", "numeros": nums, "caracteres": len(corpo)})
    SAIDA.write_text(json.dumps({"coletado_em": date.today().isoformat(), "cases": cases}, ensure_ascii=False, indent=1), encoding="utf-8")
    com = [c for c in cases if c["numeros"]]
    print(f"[OK] {len(cases)} cases lidos, {len(com)} com números, {sum(len(c['numeros']) for c in cases)} números -> {SAIDA}")
    for u, e in falhas:
        print(f"[X] {u}: {e}")
    curtos = [c["slug"] for c in cases if c["caracteres"] < 800]
    if curtos:
        print(f"[!] {len(curtos)} cases com pouco texto (conferir o corte do corpo): {', '.join(curtos[:10])}")


if __name__ == "__main__":
    main()
