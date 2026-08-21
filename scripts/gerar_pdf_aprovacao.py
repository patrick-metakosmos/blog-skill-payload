# -*- coding: utf-8 -*-
"""Monta um HTML de impressao com os dois artigos e gera PDF via Chrome headless."""
import re, os, io, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")

ARTIGOS = [
    {
        "arquivo": os.path.join(OUT, "provador-virtual-ecommerce-moda", "artigo.html"),
        "veiculo": "Blog metaKosmos",
        "etiqueta": "mK",
        "tom": "Comercial",
        "status": "Rascunho já criado no Payload (post ID 68)",
        "seo": "Provador virtual no e-commerce de moda: venda mais",
        "meta": "Provador virtual de moda com IA: recupere parte dos 98 de cada 100 que "
                "abandonam, reduza devoluções em até 61% e corte até 90% do shooting.",
        "slug": "provador-virtual-ecommerce-moda",
    },
    {
        "arquivo": os.path.join(OUT, "_WAKE-nao-publicar-no-payload",
                                "inovacao-ecommerce-processo", "artigo.html"),
        "veiculo": "Blog da Wake",
        "etiqueta": "Wake",
        "tom": "Neutro / editorial de plataforma",
        "status": "Rascunho para o time da Wake revisar e publicar",
        "seo": "Inovação no e-commerce: virou processo, não projeto",
        "meta": "3D, realidade aumentada e provador virtual ficaram acessíveis. Como "
                "estruturar um teste com métrica clara e sem travar a operação.",
        "slug": "inovacao-ecommerce-processo",
    },
]


def preparar(html):
    """Troca <img> por uma marcacao de posicao e destaca placeholders."""
    def img_repl(m):
        src, alt = m.group(1), m.group(2)
        return ('<div class="imgph"><span class="imgph-tag">IMAGEM</span>'
                '<span class="imgph-alt">%s</span>'
                '<span class="imgph-src">%s</span></div>' % (alt, src))
    html = re.sub(r'<img\s+src="([^"]+)"\s+alt="([^"]*)"\s*/?>', img_repl, html)
    html = re.sub(r'\[(INSERIR_[A-Z_]+)\]', r'<span class="ph">[\1]</span>', html)
    # h1 do artigo vira h2 do documento (o h1 do PDF e o titulo geral)
    html = re.sub(r'<h1>(.*?)</h1>', r'<h2 class="titulo-artigo">\1</h2>', html, flags=re.S)
    html = re.sub(r'<h4>', '<h5>', html); html = re.sub(r'</h4>', '</h5>', html)
    html = re.sub(r'<h3>', '<h4>', html); html = re.sub(r'</h3>', '</h4>', html)
    html = re.sub(r'<h2(?! class)>', '<h3>', html); html = re.sub(r'</h2>', '</h3>', html)
    html = html.replace('<h3 class="titulo-artigo">', '<h2 class="titulo-artigo">')
    return html


def contar(html):
    t = re.sub(r"<[^>]+>", " ", html)
    t = re.sub(r"\s+", " ", t)
    return len(t.split())


CSS = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
* { box-sizing: border-box; }
body { font-family: Georgia, "Times New Roman", serif; font-size: 10.5pt;
       line-height: 1.62; color: #1a1a1a; margin: 0; }
h1, h2, h3, h4, h5, .sans { font-family: "Helvetica Neue", Arial, Helvetica, sans-serif; }

.capa { height: 245mm; display: flex; flex-direction: column; justify-content: center;
        page-break-after: always; }
.capa .kicker { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 9pt;
        letter-spacing: .22em; text-transform: uppercase; color: #666; margin-bottom: 14mm; }
.capa h1 { font-size: 30pt; line-height: 1.15; margin: 0 0 8mm 0; font-weight: 700; }
.capa .sub { font-size: 12pt; color: #444; margin-bottom: 16mm; max-width: 135mm; }
.capa table { width: 100%; border-collapse: collapse; font-family: "Helvetica Neue", Arial, sans-serif;
        font-size: 9.5pt; }
.capa td { padding: 3.2mm 0; border-bottom: 1px solid #e2e2e2; vertical-align: top; }
.capa td:first-child { width: 42mm; color: #777; text-transform: uppercase;
        letter-spacing: .07em; font-size: 8pt; padding-top: 4mm; }

.ficha { page-break-after: always; }
.ficha h2 { font-size: 16pt; margin: 0 0 6mm 0; }
.ficha table { width: 100%; border-collapse: collapse; font-family: "Helvetica Neue", Arial, sans-serif;
        font-size: 9.5pt; margin-bottom: 10mm; }
.ficha th { text-align: left; background: #f2f2f2; padding: 2.5mm 3mm; font-size: 8.5pt;
        text-transform: uppercase; letter-spacing: .06em; border-bottom: 2px solid #ddd; }
.ficha td { padding: 2.8mm 3mm; border-bottom: 1px solid #eaeaea; vertical-align: top; }
.ficha .nota { font-size: 9.5pt; background: #faf7ef; border-left: 3px solid #d8c48a;
        padding: 4mm 5mm; margin: 4mm 0; font-family: "Helvetica Neue", Arial, sans-serif;
        line-height: 1.5; }

.artigo { page-break-before: always; }
.faixa { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 8.5pt;
        letter-spacing: .16em; text-transform: uppercase; color: #fff; background: #000;
        display: inline-block; padding: 1.8mm 4mm; margin-bottom: 6mm; }
.faixa.wake { background: #4a4a4a; }
h2.titulo-artigo { font-size: 20pt; line-height: 1.2; margin: 0 0 3mm 0; }
.linha-meta { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 8.5pt; color: #777;
        border-bottom: 2px solid #000; padding-bottom: 4mm; margin-bottom: 8mm; }
.artigo h3 { font-size: 13.5pt; margin: 9mm 0 3mm 0; line-height: 1.25;
        page-break-after: avoid; border-top: 1px solid #ddd; padding-top: 4mm; }
.artigo h4 { font-size: 11pt; margin: 6mm 0 2mm 0; color: #222; page-break-after: avoid; }
.artigo h5 { font-size: 10pt; margin: 5mm 0 2mm 0; color: #444; font-style: italic;
        page-break-after: avoid; }
.artigo p { margin: 0 0 3.4mm 0; orphans: 2; widows: 2; }
.artigo ul { margin: 0 0 4mm 0; padding-left: 6mm; }
.artigo li { margin-bottom: 2mm; }
.artigo blockquote { margin: 5mm 0; padding: 4mm 6mm; background: #f4f4f4;
        border-left: 3px solid #000; page-break-inside: avoid; }
.artigo blockquote p { margin: 0; font-size: 10pt; }
.artigo a { color: #000; text-decoration: none; border-bottom: 1px dotted #999; }
.artigo hr { border: 0; border-top: 1px solid #ddd; margin: 7mm 0; }

.imgph { border: 1px dashed #bbb; background: #fafafa; padding: 3.5mm 4mm; margin: 5mm 0;
        font-family: "Helvetica Neue", Arial, sans-serif; page-break-inside: avoid; }
.imgph-tag { font-size: 7.5pt; letter-spacing: .14em; color: #999; display: block;
        margin-bottom: 1.5mm; }
.imgph-alt { font-size: 9.5pt; color: #333; display: block; }
.imgph-src { font-size: 8pt; color: #999; display: block; margin-top: 1.5mm;
        font-family: Consolas, monospace; }
.ph { background: #ffe9a8; padding: 0.6mm 2mm; font-family: Consolas, monospace;
        font-size: 9pt; border: 1px solid #e0c46a; }
"""

partes = []
partes.append("""<div class="capa">
<div class="kicker">metaKosmos &middot; Aprovação de conteúdo</div>
<h1>Dois artigos derivados do WakeCast #5</h1>
<div class="sub">Provador virtual e realidade aumentada: como vender mais no e-commerce de moda.
Episódio com Diego Santos (Wake) e Ian (metaKosmos).</div>
<table>
<tr><td>Origem</td><td>WakeCast episódio 5, 58min51s. Transcrição integral gerada com Whisper large-v3-turbo</td></tr>
<tr><td>Peças</td><td>1 artigo para o blog da metaKosmos (comercial) e 1 para o blog da Wake (neutro)</td></tr>
<tr><td>Volume</td><td>%s palavras somadas</td></tr>
<tr><td>Situação</td><td>Aguardando aprovação</td></tr>
<tr><td>Data</td><td>11 de agosto de 2026</td></tr>
</table>
</div>""")

ficha_linhas = []
corpos = []
total = 0

for a in ARTIGOS:
    html = io.open(a["arquivo"], encoding="utf-8").read()
    titulo = re.search(r"<h1>(.*?)</h1>", html, re.S).group(1)
    n = contar(html)
    total += n
    a["_n"] = n
    a["_titulo"] = titulo
    ficha_linhas.append(
        "<tr><td><strong>%s</strong><br><span style='color:#777'>%s</span></td>"
        "<td>%s</td><td>%s</td><td>%s palavras</td></tr>"
        % (a["veiculo"], a["tom"], titulo, a["status"], "{:,}".format(n).replace(",", ".")))

    corpo = preparar(html)
    cls = "faixa wake" if a["etiqueta"] == "Wake" else "faixa"
    corpos.append(
        '<div class="artigo"><span class="%s">%s &nbsp;|&nbsp; %s</span>\n%s\n'
        '<div class="linha-meta">Título SEO: %s &nbsp;&middot;&nbsp; Slug: %s &nbsp;&middot;&nbsp; '
        '%s palavras<br>Meta description: %s</div>\n%s</div>'
        % (cls, a["veiculo"], a["tom"], corpo[:corpo.find("</h2>") + 5],
           a["seo"], a["slug"], "{:,}".format(n).replace(",", "."), a["meta"],
           corpo[corpo.find("</h2>") + 5:]))

ficha = """<div class="ficha">
<h2>O que está sendo aprovado</h2>
<table>
<tr><th>Veículo</th><th>Título</th><th>Situação</th><th>Extensão</th></tr>
__LINHAS__
</table>

<div class="nota"><strong>Os dois textos não competem entre si.</strong> Saíram da mesma entrevista,
mas atacam palavras-chave diferentes e não repetem argumento. O artigo da metaKosmos vende a solução
e usa cases com nome e métrica. O da Wake explica a decisão de compra e não cita nenhum fornecedor,
para preservar a autoridade neutra de um editorial de plataforma.</div>

<div class="nota"><strong>Pontos que dependem da sua conferência.</strong>
Nenhum valor monetário foi publicado nos dois textos, conforme a regra padrão do blog.
No artigo da metaKosmos, dois números da entrevista precisam de validação antes de ir ao ar:
o percentual exato de aumento de conversão da Gregory (no episódio ficou em "dois dígitos") e o
tamanho do estudo State of Immersive and Agentic Commerce (foram citadas 300 páginas; por isso o
texto não menciona número de páginas). O dado de adoção citado no episódio como "6,5% de early
adopters" foi omitido dos dois artigos, porque a curva de Rogers usa 13,5%.</div>

<div class="nota"><strong>No artigo da Wake há um marcador a preencher:</strong>
<span class="ph">[INSERIR_CTA_WAKE]</span>, no fim do texto. Nenhuma URL da Wake foi inventada.
As imagens aparecem aqui como caixas tracejadas indicando posição e descrição.</div>
</div>""".replace("__LINHAS__", "\n".join(ficha_linhas))

doc = ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
       "<title>Aprovacao de conteudo</title><style>%s</style></head><body>%s%s%s</body></html>"
       % (CSS, partes[0] % "{:,}".format(total).replace(",", "."), ficha, "\n".join(corpos)))

html_path = os.path.join(OUT, "_aprovacao-artigos-wakecast.html")
io.open(html_path, "w", encoding="utf-8").write(doc)
print("[OK] HTML montado:", html_path)

pdf_path = os.path.join(OUT, "Aprovacao-artigos-WakeCast.pdf")
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(chrome):
    chrome = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                "--print-to-pdf=" + pdf_path, "file:///" + html_path.replace("\\", "/")],
               check=True, timeout=180)
print("[OK] PDF gerado:", pdf_path)
print("[i] %s palavras no total | %d artigos" % ("{:,}".format(total).replace(",", "."), len(ARTIGOS)))
