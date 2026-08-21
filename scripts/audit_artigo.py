# -*- coding: utf-8 -*-
"""Auditoria de formato + anti-IA do artigo.html (passo 8.5 da SKILL.md)."""
import re, sys, os, io

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slug = sys.argv[1]
path = os.path.join(BASE, "output", slug, "artigo.html")
html = io.open(path, encoding="utf-8").read()

def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()

print("=" * 62)
print("AUDITORIA:", slug)
print("=" * 62)

# --- FORMATO PAYLOAD ---
proib = {
    "<div": len(re.findall(r"<div", html, re.I)),
    "style=": len(re.findall(r"style\s*=", html, re.I)),
    "wp-block": len(re.findall(r"wp-block", html, re.I)),
    "<button": len(re.findall(r"<button", html, re.I)),
    "<!-- wp": len(re.findall(r"<!--\s*wp", html, re.I)),
    "<table": len(re.findall(r"<table", html, re.I)),
}
print("\n[FORMATO PAYLOAD]")
for k, v in proib.items():
    print("  %-10s %d %s" % (k, v, "OK" if v == 0 else "<<< FALHA"))

for tag in ["p", "h2", "h3", "h4", "li", "ul", "blockquote", "a", "strong", "em", "u"]:
    o = len(re.findall(r"<%s[ >]" % tag, html))
    c = len(re.findall(r"</%s>" % tag, html))
    if o != c:
        print("  DESBALANCEADO <%s>: %d abre / %d fecha  <<< FALHA" % (tag, o, c))
h1 = len(re.findall(r"<h1[ >]", html))
print("  <h1>: %d %s" % (h1, "OK" if h1 == 1 else "<<< FALHA"))
print("  headings: h2=%d h3=%d h4=%d" % (
    len(re.findall(r"<h2[ >]", html)), len(re.findall(r"<h3[ >]", html)),
    len(re.findall(r"<h4[ >]", html))))
print("  blockquotes: %d (meta 2-4)" % len(re.findall(r"<blockquote", html)))
print("  <hr>: %d" % len(re.findall(r"<hr", html)))

# --- IMAGENS vs CATALOGO ---
cat = io.open(os.path.join(BASE, "references", "media-payload.md"), encoding="utf-8").read()
nomes = set(re.findall(r"^\|\s*`([^`]+)`", cat, re.M))
imgs = re.findall(r'<img\s+src="([^"]+)"\s+alt="([^"]*)"', html)
todas = re.findall(r"<img", html)
print("\n[IMAGENS] %d encontradas, %d com src+alt" % (len(todas), len(imgs)))
for src, alt in imgs:
    ok = src in nomes
    print("  %-70s %s%s" % (src, "no catalogo" if ok else "<<< FORA DO CATALOGO",
                            "" if alt.strip() else "  <<< SEM ALT"))

# --- ANTI-IA PROGRAMATICA ---
texto = strip_tags(html)
print("\n[ANTI-IA]")
em = texto.count("—")
print("  em dash (—): %d (limite 0) %s" % (em, "OK" if em == 0 else "<<< FALHA"))

naoe = re.findall(r"[Nn]ão é [^.,;!?]{1,60}?, é |[Nn]ão é [^.]{1,50}?\. É |pergunta não é|[Nn]ão é [^.,;]{1,40} nem ", texto)
print("  'Não é X, é Y': %d (limite 2) %s" % (len(naoe), "OK" if len(naoe) <= 2 else "<<< FALHA"))
for m in naoe:
    print("      -> %s" % m.strip())

concl = re.findall(r"\b(Em conclusão|Para concluir|Concluindo|Em resumo|Resumindo|Em suma|Por fim|Para finalizar|Em última análise|Em síntese)\b", texto, re.I)
print("  frases-conclusão: %d (limite 0) %s" % (len(concl), "OK" if not concl else "<<< FALHA " + str(concl)))

vocab = re.findall(r"\b(Adicionalmente|panorama|alavancar|sinergia|holístic\w+|multifacetad\w+|intrincad\w+|revolucionári\w+|disruptiv\w+|transformador\w*)\b", texto, re.I)
print("  vocabulário de IA: %d %s" % (len(vocab), "OK" if not vocab else "<<< REVISAR " + str(set(vocab))))

# --- PARAGRAFOS ---
paras = re.findall(r"<p>(.*?)</p>", html, re.S)
faq_start = html.find("Perguntas frequentes")
corpo_paras, faq_paras = [], []
for m in re.finditer(r"<p>(.*?)</p>", html, re.S):
    (faq_paras if m.start() > faq_start > 0 else corpo_paras).append(strip_tags(m.group(1)))

longos = [(len(p.split()), p[:70]) for p in corpo_paras if len(p.split()) > 40]
print("\n[PARAGRAFOS]")
print("  corpo: %d parágrafos | >40 palavras: %d %s" % (
    len(corpo_paras), len(longos), "OK" if not longos else "<<< FALHA"))
for n, t in longos:
    print("      %d palavras: %s..." % (n, t))

# --- CONTAGEM ---
def wc(s):
    return len(re.sub(r"[^\w\sÀ-ÿ]", " ", s).split())

h1txt = strip_tags(re.search(r"<h1>(.*?)</h1>", html, re.S).group(1))
corpo_html = html[:faq_start] if faq_start > 0 else html
faq_html = html[faq_start:] if faq_start > 0 else ""
corpo_w = wc(strip_tags(corpo_html))
faq_w = wc(strip_tags(faq_html))
print("\n[CONTAGEM]")
print("  corpo (sem FAQ): %d palavras (piso 2000) %s" % (corpo_w, "OK" if corpo_w >= 2000 else "<<< FALHA"))
print("  FAQ: %d palavras" % faq_w)
print("  total: %d palavras" % (corpo_w + faq_w))

faq_qs = re.findall(r"<h3>(.*?)</h3>", faq_html, re.S)
print("  FAQ perguntas: %d (piso 10) %s" % (len(faq_qs), "OK" if len(faq_qs) >= 10 else "<<< FALHA"))
for i, (q, a) in enumerate(zip(faq_qs, faq_paras), 1):
    n = len(a.split())
    flag = "" if 60 <= n <= 90 else "  <<< fora de 60-90"
    print("    %2d. %-58s %d palavras%s" % (i, strip_tags(q)[:58], n, flag))

# --- LINKS ---
links = re.findall(r'href="([^"]+)"', html)
print("\n[LINKS] %d totais" % len(links))
sem_utm = [l for l in links if "utm_source" not in l]
print("  sem UTM: %d %s" % (len(sem_utm), "OK" if not sem_utm else str(sem_utm)))
internos = [l for l in links if not l.startswith("http")]
print("  internos: %d | externos: %d" % (len(internos), len(links) - len(internos)))
for l in sorted(set(links)):
    print("    %s" % l.split("?")[0])

# --- VOZ mK ---
print("\n[VOZ mK]")
checks = [
    ("'Spoiler:'", len(re.findall(r"Spoiler:", texto))),
    ("parênteses coloquiais", len(re.findall(r"\([^)]{5,90}\)", texto))),
    ("metaKosmos (mencoes)", len(re.findall(r"metaKosmos", texto))),
    ("mK Fashion+/3D Shop/Beauty", len(re.findall(r"mK (Fashion\+|3D Shop|Beauty)", texto))),
]
for nome, n in checks:
    print("  %-28s %d" % (nome, n))
print()
