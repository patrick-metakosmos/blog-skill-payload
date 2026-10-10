# -*- coding: utf-8 -*-
"""Auditoria de formato + anti-IA do artigo.html (passo 8.5 da SKILL.md)."""
import re, sys, os, io, json, unicodedata
from urllib.parse import urlparse
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slug = sys.argv[1]
# aceita também o caminho de um artigo.html (o otimizador trabalha em otimizador/trabalho/<slug>/)
path = slug if slug.endswith(".html") else os.path.join(BASE, "output", slug, "artigo.html")
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
alt_cat = dict(re.findall(r"^\|\s*`([^`]+)`.*?\|\s*([^|]*?)\s*\|\s*$", cat, re.M))
for src, alt in imgs:
    ok = src in nomes
    print("  %-70s %s%s" % (src, "no catalogo" if ok else "<<< FORA DO CATALOGO",
                            "" if alt.strip() else "  <<< SEM ALT"))

# R1 (BLOQUEADOR): nenhuma imagem do artigo pode ser logo de marca.
# "catálogo" contém "logo" e não conta; alt descritivo tipo "com o logo X" também não.
_fp = re.compile(r"cat[aá]logo|com o logo|com logo|proje[cç]", re.I)
def _eh_logo(nome, texto_alt):
    return bool(re.search(r"logo", _fp.sub("", nome or ""), re.I)
                or re.search(r"logo", _fp.sub("", texto_alt or ""), re.I))
logos = [src for src, alt in imgs if _eh_logo(src, alt) or _eh_logo(src, alt_cat.get(src, ""))]
print("  imagem-logo: %d (limite 0) %s" % (
    len(logos), "OK" if not logos else "<<< FALHA " + str(logos)))

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
DOMINIOS_MK = ("metakosmos.com.br", "www.metakosmos.com.br")
FORMULARIO = "form.respondi.app"

def host_de(l):
    return urlparse(l).netloc.lower() if l.startswith("http") else ""

internos = [l for l in links if not l.startswith("http") or host_de(l) in DOMINIOS_MK]
formularios = [l for l in links if host_de(l) == FORMULARIO]
externos = [l for l in links if l.startswith("http") and host_de(l) not in DOMINIOS_MK and host_de(l) != FORMULARIO]
print("  internos: %d | formulário: %d | fontes externas: %d" % (len(internos), len(formularios), len(externos)))

# NOVA REGRA (10/2026): link interno NÃO leva UTM (reinicia a sessão no GA4 e apaga a origem real).
# O link do formulário (outro domínio) mantém UTM: é como a origem chega no Respondi.
internos_utm = [l for l in internos if "utm_" in l]
print("  links internos com UTM: %d (limite 0) %s" % (len(internos_utm), "OK" if not internos_utm else "<<< FALHA"))
for l in internos_utm[:6]:
    print("      -> %s" % l[:110])
if formularios:
    sem = [l for l in formularios if "utm_source" not in l]
    print("  link do formulário com UTM: %s" % ("OK" if not sem else "<<< FALHA (formulário sem utm_source)"))

# R7 do Guia GEO/AEO (BLOQUEADOR): 1 a 2 fontes externas reconhecidas com link visível
print("  fontes externas: %d (piso 1, teto 2) %s" % (
    len(externos), "OK" if 1 <= len(externos) <= 2 else "<<< FALHA"))
for l in externos:
    print("      -> %s" % l[:110])

# R2 (BLOQUEADOR): o estudo só é linkado pela página de captura, nunca pelo PDF.
pdf = [l for l in links if "api/media/file/State" in l or "State%20of%20Immersive" in l]
print("  link direto do PDF do estudo: %d (limite 0) %s" % (
    len(pdf), "OK" if not pdf else "<<< FALHA " + str(pdf)))
estudo = [l for l in links if "/estudo" in l]
print("  links para /estudo: %d (piso 2: citação inline + CTA final) %s" % (
    len(estudo), "OK" if len(estudo) >= 2 else "<<< FALHA"))
for l in sorted(set(links)):
    print("    %s" % l.split("?")[0])

# --- SEO / GEO / AEO (Guia GEO AEO, Orgânica abr/2026) ---
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s.lower())).strip()

print("\n[SEO/GEO]")
kw = h1txt.split(":")[0].strip()
kwn = norm(kw)
print("  keyword (abertura do H1): %s" % kw)

apos_h1 = html[html.index("</h1>") + 5:] if "</h1>" in html else html
primeiras = norm(" ".join(strip_tags(apos_h1).split()[:150]))
ok_kw = kwn in primeiras
print("  keyword nas primeiras 150 palavras (resposta direta logo na abertura): %s" % ("OK" if ok_kw else "<<< FALHA"))
h23 = [norm(strip_tags(h)) for h in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", html, re.S)]
ok_h = any(kwn in h for h in h23)
print("  keyword em algum H2/H3 (ou pergunta do FAQ): %s" % ("OK" if ok_h else "<<< FALHA"))

h2 = [strip_tags(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.S)]
interrog = re.compile(r"\?$|^(o que|como|por que|porque|quando|quanto|quantos?|qual|quais|onde|para que|quem)\b", re.I)
h2_perg = [h for h in h2 if interrog.search(h.strip())]
print("  H2 em forma de pergunta: %d de %d (meta >= 30%%) %s" % (
    len(h2_perg), len(h2), "OK" if h2 and len(h2_perg) / len(h2) >= 0.3 else "<<< REVISAR"))

todas = [f for f in re.split(r"(?<=[.!?])\s+", strip_tags(apos_h1)) if f.strip()]
longas = [f for f in todas if len(f.split()) > 25]
pct_l = len(longas) / len(todas) if todas else 0
print("  frases acima de 25 palavras (Guia R2): %d de %d (%.0f%%; meta <= 30%%) %s" % (
    len(longas), len(todas), pct_l * 100, "OK" if pct_l <= 0.30 else "<<< REVISAR"))

menc = len(re.findall(r"meta[Kk]osmos", texto))
print("  menções a metaKosmos: %d (piso 3) %s" % (menc, "OK" if menc >= 3 else "<<< FALHA"))

# título SEO e meta description (seo.json do otimizador ou metadados.md do gerador)
pasta_art = os.path.dirname(os.path.abspath(path))
seo = None
if os.path.exists(os.path.join(pasta_art, "seo.json")):
    d = json.load(io.open(os.path.join(pasta_art, "seo.json"), encoding="utf-8"))
    seo = (d.get("metaTitle", ""), d.get("metaDescription", ""))
elif os.path.exists(os.path.join(pasta_art, "metadados.md")):
    from payload_publish import parse_metadados
    m = parse_metadados(Path(pasta_art) / "metadados.md")
    seo = (m["title_seo"], m["meta_description"])
if seo is None:
    print("  título SEO / meta description: sem seo.json nem metadados.md ao lado do artigo <<< REVISAR")
else:
    ts, md = seo
    print("  título SEO: %d caracteres (limite 60) %s" % (len(ts), "OK" if 0 < len(ts) <= 60 else "<<< FALHA"))
    print("  título SEO abre pela keyword: %s" % ("OK" if norm(ts).startswith(kwn) else "<<< FALHA"))
    print("  meta description: %d caracteres (limite 155) %s" % (len(md), "OK" if 0 < len(md) <= 155 else "<<< FALHA"))
    print("  meta description com dado numérico (Guia): %s" % ("OK" if re.search(r"\d", md) else "<<< REVISAR"))

# --- CONCORRENTES (regra 10/2026: nenhum nome; comparar vantagens sem citar) ---
cc_path = os.path.join(BASE, "references", "concorrentes.md")
nomes = sorted(set(re.findall(r"^\|\s*\*\*([^*|]+?)\*\*", io.open(cc_path, encoding="utf-8").read(), re.M)))
alvo = norm(texto + " " + " ".join(links))
achados = [n for n in nomes if re.search(r"\b" + re.escape(norm(n)) + r"\b", alvo)]
print("\n[CONCORRENTES] %d nomes monitorados | citados no artigo: %d (limite 0) %s" % (
    len(nomes), len(achados), "OK" if not achados else "<<< FALHA"))
for n in achados:
    print("      -> %s" % n)

# --- PREÇOS (só valores aprovados em references/precos-aprovados.json; sem arquivo = nenhum) ---
aprov_path = os.path.join(BASE, "references", "precos-aprovados.json")
aprov = []
if os.path.exists(aprov_path):
    aprov = [norm(x) for x in json.load(io.open(aprov_path, encoding="utf-8")).get("valores_aprovados", [])]
reais, fora = [], []
for m in re.finditer(r"R\$\s?\d[\d.,]*(?:\s?(?:mil|mi|milh[ãa]o|milh[õo]es|k)\b)?", texto):
    reais.append(m.group(0))
    antes = texto[max(0, m.start() - 20):m.start()].lower()
    if norm(m.group(0)) not in aprov or "a partir de" not in antes:
        fora.append(m.group(0) + ("" if "a partir de" in antes else " (sem 'a partir de')"))
print("[PREÇOS] valores em R$ no texto: %d | fora da lista aprovada: %d (limite 0) %s" % (
    len(reais), len(fora), "OK" if not fora else "<<< FALHA"))
for r in fora[:6]:
    print("      -> %s" % r)

# --- NÚMEROS: base única references/numeros-oficiais.json (aviso, não bloqueia) ---
base_path = os.path.join(BASE, "references", "numeros-oficiais.json")
if os.path.exists(base_path):
    base = json.load(io.open(base_path, encoding="utf-8"))["numeros"]
    chave = lambda v: re.sub(r"[\s+]", "", v.lower()).replace("milhões", "mi").replace("milhão", "mi")
    conhecidos = {chave(n["valor"]): n for n in base}
    usados = [re.sub(r"\s+", " ", m).strip() for m in re.findall(
        r"(?<![\d\w])[+\-]?\d[\d.,]*\s?(?:%|x\b|X\b|milh[ãõ][eo]s?|\bmi\b|\bmil\b)", texto)]
    fora_base = sorted({u for u in usados if chave(u) not in conhecidos})
    pend = sorted({u for u in usados if chave(u) in conhecidos and conhecidos[chave(u)].get("status") != "confirmado"})
    print("[NÚMEROS] %d números com unidade | fora da base: %d | com decisão pendente: %d" % (
        len(usados), len(fora_base), len(pend)))
    if fora_base:
        print("      fora da base (conferir a fonte): %s" % ", ".join(fora_base[:18]))
    if pend:
        print("      <<< REVISAR pendentes: %s" % ", ".join(pend))
    sem_fonte = [f for f in json.load(io.open(base_path, encoding="utf-8")).get("frases_sem_fonte", [])
                 if f["frase"].lower() in texto.lower()]
    for f in sem_fonte:
        print("      <<< REVISAR alegação sem fonte no estudo: \"%s\" (%s)" % (f["frase"], f["motivo"]))

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
