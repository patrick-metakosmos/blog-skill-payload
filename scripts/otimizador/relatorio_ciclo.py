# -*- coding: utf-8 -*-
"""Gera o relatório visual de resultados e novas otimizações (uma página, para o CEO).

Lê os dados que o painel.py já embute em otimizador/painel/index.html (rode o painel.py antes), mais os
artigos de otimizador/trabalho/<slug>/, e grava otimizador/relatorio/index.html. Fontes e logo são os mesmos
do painel (publique com files apontando para o artifact do painel).

Uso:
    python scripts/otimizador/painel.py
    python scripts/otimizador/relatorio_ciclo.py
"""
import html
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import SKILL_DIR  # noqa: E402

PAINEL = SKILL_DIR / "otimizador" / "painel" / "index.html"
TRABALHO = SKILL_DIR / "otimizador" / "trabalho"
SAIDA = SKILL_DIR / "otimizador" / "relatorio" / "index.html"

# o que mudou em cada artigo do ciclo mais novo (texto curto, escrito a partir do feito.md de cada um)
NOTAS = {
    "videos-publicitarios-com-ia-guia-completo-para-marcas": "Abertura com a definição e o ângulo de contratar, produzir e medir. Fonte do Google sobre Brand Lift. Saíram o 28x de Nielsen, o R$ 500 mil de comercial de TV e outros números sem fonte.",
    "mk-shop-the-look-ia-look-completo-ecommerce": "Vira o conteúdo educativo e encaminha para as páginas do produto, para não disputar a busca \"mk shop\" com elas. Saíram o 97% de precisão, o NPS 98 e os prazos sem base.",
    "mk-labs-creative-house-projetos-imersivos": "Preserva \"metaKosmos\" e \"mK Labs\" no título, porque quase toda busca é de marca. Abertura rápida, mKases com número e CTA isolado. Saíram clientes que são do provador, não do Labs.",
    "como-reduzir-devolucoes-ecommerce-moda": "Responde na primeira frase, que era o ponto forte da busca em linguagem natural. O -61% entra só como potencial do estudo. Saíram 10 números sem fonte e um exemplo que o mKase da Gregory não sustenta.",
}
VIGIAR = {"mk-labs-creative-house-projetos-imersivos": "Quase toda busca é de marca. Se perder posição em \"mk labs\", reverter.",
          "mk-shop-the-look-ia-look-completo-ecommerce": "Busca \"mk shop\" também traz a página do mK 3D. Medir se não canibalizou."}


def num(s):
    return int(s.replace(".", ""))


def parse_resultado(txt):
    m = re.search(r"impressoes (\d+) → (\d+), ([+-]\d+)%; posição ([\d.]+) → ([\d.]+)", txt or "")
    if not m:
        return None
    return {"imp0": int(m[1]), "imp1": int(m[2]), "var": int(m[3]), "pos0": float(m[4]), "pos1": float(m[5]),
            "janela": int(re.search(r"janelas de (\d+) dias", txt)[1]) if re.search(r"janelas de (\d+) dias", txt) else None}


def faq_count(slug):
    p = TRABALHO / slug / "artigo.html"
    if not p.exists():
        return None
    return len(re.findall(r"<h3>[^<]*\?</h3>", p.read_text(encoding="utf-8")))


def main():
    h = PAINEL.read_text(encoding="utf-8")
    D = json.loads(re.search(r'<script id="dados" type="application/json">(.*?)</script>', h, re.S).group(1))
    ots = D["otimizados"]
    for o in ots:
        o["res"] = parse_resultado(o.get("resultado"))
        o["faq"] = faq_count(o["slug"])
        o["nota"] = NOTAS.get(o["slug"], "")
        o["vigiar"] = VIGIAR.get(o["slug"], "")
    ciclos = D["ciclos"]
    dados = {"gerado_em": D["gerado_em"], "ciclos": ciclos, "medicao": D.get("medicao"), "otimizados": ots}
    # a primeira data de cada ciclo libera o artigo de novo 28 dias depois
    libera = sorted({(date.fromisoformat(o["data"]) + timedelta(days=28)).isoformat() for o in ots if o["data"]})
    dados["libera"] = libera
    saida = TEMPLATE.replace("__DADOS__", json.dumps(dados, ensure_ascii=False).replace("</", "<\\/"))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(saida, encoding="utf-8")
    print(f"[OK] {SAIDA} | {len(ots)} artigos, {len(ciclos)} ciclos")


TEMPLATE = r"""<title>Resultados do Otimizador</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&display=swap">
<style>
@font-face{font-family:"Helvetica";src:url("fonts/HelveticaNeueLight.otf") format("opentype");font-weight:300;font-display:swap}
@font-face{font-family:"Helvetica";src:url("fonts/HelveticaNeueBold.otf") format("opentype");font-weight:700;font-display:swap}
@font-face{font-family:"Helvetica";src:url("fonts/HelveticaNeueHeavy.otf") format("opentype");font-weight:800;font-display:swap}
/* layout: uma coluna de leitura. Primeiro o veredito do ciclo 1 (barras antes/depois), depois as 4 novas reescritas, depois o calendário */
:root{
  color-scheme:dark;
  --black:#000000;--white:#FFFFFF;--card:#080808;
  --text-2:#AAAAAA;--text-3:#868686;
  --line:rgba(255,255,255,0.08);--line-2:rgba(255,255,255,0.24);
  --accent:#00D97E;--accent-ink:#000000;
  --bar-antes:#6B7178;--bar-depois:#00AD64;--bar-pior:#3A7BEF;--grid:#1A1A1A;
  --display:'Anton',Impact,sans-serif;
  --body:'Helvetica','Helvetica Neue',Arial,sans-serif;
}
*{box-sizing:border-box}
html{background:var(--black)}
body{margin:0;background:var(--black);color:var(--white);font-family:var(--body);font-weight:300;font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding-block:40px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:64px}
h1,h2,h3{font-family:var(--display);font-weight:400;text-transform:uppercase;margin:0;text-wrap:balance}
h1{font-size:clamp(40px,7vw,72px);line-height:1}
h2{font-size:clamp(28px,4.5vw,48px);line-height:1.05}
h3{font-size:22px;line-height:1.1}
p{margin:0;max-width:66ch}
a{color:var(--white)}
.label{font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase}
.sub{font-size:clamp(16px,1.6vw,19px);color:var(--text-2);max-width:640px}
.sub b,.lede b{color:var(--white);font-weight:700}
.sec{display:flex;flex-direction:column;gap:32px}
.head{display:flex;flex-direction:column;gap:16px}
.top{display:flex;flex-direction:column;gap:32px}
.brand{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.brand img{height:32px;width:auto}
.brand span{font-size:12px;color:var(--text-2)}
.pills{display:flex;flex-wrap:wrap;gap:8px}
.pill{display:inline-flex;align-items:center;gap:8px;padding:5px 12px;border-radius:8px;font-size:10px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;border:1px solid var(--line-2)}
.pill.on{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.kpi{background:var(--black);padding:32px 16px 16px;display:flex;flex-direction:column;gap:8px}
.kpi .v{font-weight:700;font-size:clamp(32px,3.6vw,44px);line-height:1;letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.kpi .v small{font-size:.5em;font-weight:300;color:var(--text-2)}
.kpi .d{font-size:13px;color:var(--text-2)}
.kpi .d b{color:var(--accent);font-weight:700}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:32px;display:flex;flex-direction:column;gap:16px;min-width:0}
.ctitle{font-weight:700;font-size:16px}
.csub{font-size:13px;color:var(--text-2)}
.rows{display:flex;flex-direction:column;gap:24px}
.row{display:grid;grid-template-columns:minmax(0,260px) minmax(0,1fr) 120px;gap:16px 24px;align-items:center}
.row .nm{font-weight:700;font-size:14px;line-height:1.35}
.row .nm small{display:block;font-weight:300;font-size:12px;color:var(--text-3)}
.pair{display:flex;flex-direction:column;gap:6px}
.bar{display:grid;grid-template-columns:1fr 56px;align-items:center;gap:8px;font-variant-numeric:tabular-nums;font-size:12px;color:var(--text-2)}
.track{height:10px;background:var(--grid);border-radius:5px;position:relative}
.track i{position:absolute;inset:0 auto 0 0;border-radius:5px;display:block}
.bar.a i{background:var(--bar-antes)}
.bar.d i{background:var(--bar-depois)}
.bar.d{color:var(--white);font-weight:700}
.delta{text-align:right}
.delta b{display:block;font-size:24px;font-weight:700;color:var(--accent);line-height:1;font-variant-numeric:tabular-nums}
.delta span{font-size:12px;color:var(--text-2);font-variant-numeric:tabular-nums}
.delta .pos-pior{color:var(--bar-pior)}
.legend{display:flex;flex-wrap:wrap;gap:8px 24px;font-size:13px;color:var(--text-2)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}
.leitura{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:32px}
.leit{border-top:2px solid var(--accent);padding-top:16px;display:flex;flex-direction:column;gap:8px}
.leit p{color:var(--text-2)}
.leit .big{font-weight:700;font-size:15px;color:var(--white)}
.arts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:16px}
.art{background:var(--card);border:1px solid var(--line);border-radius:32px;padding:32px;display:flex;flex-direction:column;gap:16px;min-width:0}
.top2{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:8px;font-size:10px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;border:1px solid var(--line-2)}
.chip i{width:8px;height:8px;border-radius:50%}
.small{font-size:12px;color:var(--text-3)}
.novo{font-weight:700;font-size:17px;line-height:1.35}
.velho{font-size:13px;color:var(--text-3);text-decoration:line-through;text-decoration-color:var(--line-2)}
.mets{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;border-top:1px solid var(--line);padding-top:16px}
.met .k{font-size:10px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-3);display:block}
.met .val{font-size:16px;font-weight:700;font-variant-numeric:tabular-nums}
.met .val s{font-weight:300;color:var(--text-3);text-decoration:none;margin-right:2px}
.words{display:flex;flex-direction:column;gap:8px;font-size:13px;color:var(--text-2)}
.wr{display:grid;grid-template-columns:48px 1fr 80px;align-items:center;gap:8px;font-variant-numeric:tabular-nums}
.goal{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--text-2)}
.nota{color:var(--text-2);font-size:13px}
.vig{border:1px dashed var(--line-2);border-radius:8px;padding:8px 16px;font-size:13px;color:var(--text-2)}
.vig b{color:var(--white);font-weight:700}
.tl{display:flex;flex-direction:column;border-left:1px solid var(--line-2);margin-left:6px}
.ev{position:relative;padding:0 0 24px 32px;display:flex;flex-direction:column;gap:2px}
.ev:last-child{padding-bottom:0}
.ev::before{content:"";position:absolute;left:-6px;top:6px;width:11px;height:11px;border-radius:50%;background:var(--black);border:2px solid var(--line-2)}
.ev.ok::before{background:var(--accent);border-color:var(--accent)}
.ev .w{font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;color:var(--text-2)}
.ev .t{font-size:15px}
.foot{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--text-3);border-top:1px solid var(--line);padding-top:16px}
@media (max-width:760px){
  .row{grid-template-columns:1fr}
  .delta{text-align:left;display:flex;gap:16px;align-items:baseline}
  .card,.art{padding:24px}
  .mets{grid-template-columns:repeat(3,1fr)}
}
@media (prefers-reduced-motion:no-preference){.track i{transition:width .4s ease}}
</style>

<div class="wrap">
  <header class="top">
    <div class="brand"><img src="assets/logo-mk-white.png" alt="metaKosmos"><span id="quando"></span></div>
    <h1>Resultados do Otimizador</h1>
    <p class="sub" id="lede"></p>
    <div class="pills" id="pills"></div>
  </header>

  <section class="sec" aria-labelledby="h1r">
    <div class="head">
      <span class="label">Ciclo 2026-S41 · medido em 22/10</span>
      <h2 id="h1r">O primeiro ciclo</h2>
      <p class="sub" id="sub-r"></p>
    </div>
    <div class="kpis" id="kpis"></div>
    <div class="card">
      <div><div class="ctitle">Impressões no Google, 12 dias antes e 12 dias depois</div>
      <div class="csub">Janelas de tamanho igual em volta da data da reescrita (07/10). Uma impressão é uma vez que o artigo apareceu numa busca.</div></div>
      <div class="legend"><span><i style="background:var(--bar-antes)"></i>Antes</span><span><i style="background:var(--bar-depois)"></i>Depois</span></div>
      <div class="rows" id="rows"></div>
    </div>
    <div class="leitura" id="leitura"></div>
  </section>

  <section class="sec" aria-labelledby="h2r">
    <div class="head">
      <span class="label" id="eb2"></span>
      <h2 id="h2r">As novas otimizações</h2>
      <p class="sub" id="sub-n"></p>
    </div>
    <div class="arts" id="arts"></div>
  </section>

  <section class="sec" aria-labelledby="h3r">
    <div class="head">
      <span class="label">A cada 15 dias</span>
      <h2 id="h3r">O que vem agora</h2>
    </div>
    <div class="card"><div class="tl" id="tl"></div></div>
  </section>

  <footer class="foot" id="foot"></footer>
</div>

<script id="dados" type="application/json">__DADOS__</script>
<script>
(function(){
const D = JSON.parse(document.getElementById('dados').textContent);
const nf = new Intl.NumberFormat('pt-BR');
const nf1 = new Intl.NumberFormat('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1});
const dBR = iso => { const [y,m,d] = iso.slice(0,10).split('-'); return `${d}/${m}/${y}`; };
const S41 = D.otimizados.filter(o => o.ciclo === D.ciclos[0].ciclo && o.res);
const novo = D.ciclos[D.ciclos.length-1];
const NOVOS = D.otimizados.filter(o => o.ciclo === novo.ciclo);

document.getElementById('quando').textContent = 'Atualizado em ' + D.gerado_em;
document.getElementById('lede').innerHTML = `Os ${S41.length} artigos do primeiro ciclo foram medidos e <b>todos ganharam impressões</b>. No mesmo dia, o segundo ciclo colocou <b>${NOVOS.length} artigos novos</b> no ar. Aqui está o que mudou e o que ainda falta provar.`;
document.getElementById('pills').innerHTML =
  `<span class="pill on">${S41.length} de ${S41.length} subiram em impressões</span>`
  + `<span class="pill">${NOVOS.length} reescritos em ${dBR(novo.data)}</span>`
  + (D.medicao ? `<span class="pill">Próxima medição ${dBR(D.medicao)}</span>` : '');

/* ciclo 1 */
const i0 = S41.reduce((a,o)=>a+o.res.imp0,0), i1 = S41.reduce((a,o)=>a+o.res.imp1,0);
const subiu = S41.filter(o=>o.res.pos1 < o.res.pos0).length, igual = S41.filter(o=>o.res.pos1 === o.res.pos0).length, desceu = S41.length - subiu - igual;
const maior = [...S41].sort((a,b)=>b.res.var-a.res.var)[0];
document.getElementById('sub-r').innerHTML = `Somando os ${S41.length} artigos, as impressões foram de <b>${nf.format(i0)}</b> para <b>${nf.format(i1)}</b> em janelas iguais de ${S41[0].res.janela} dias. Ainda é uma leitura inicial: o volume é pequeno e os dados vão até 18/10.`;
document.getElementById('kpis').innerHTML = [
  [`${S41.length}<small> / ${S41.length}</small>`, 'Artigos que melhoraram', 'em impressões, janelas iguais antes e depois'],
  [`+${Math.round((i1/i0-1)*100)}%`, 'Impressões somadas', `${nf.format(i0)} para ${nf.format(i1)} nos ${S41.length} artigos`],
  [`+${maior.res.var}%`, 'Maior alta', `${maior.titulo_depois.split(':')[0]}`],
  [`${subiu} · ${igual} · ${desceu}`, 'Posição: subiu · igual · desceu', 'posição média no Google'],
].map(([v,l,d]) => `<div class="kpi"><span class="label">${l}</span><span class="v">${v}</span><span class="d">${d}</span></div>`).join('');

const max = Math.max(...S41.map(o=>o.res.imp1));
document.getElementById('rows').innerHTML = [...S41].sort((a,b)=>b.res.var-a.res.var).map(o => {
  const r = o.res, melhor = r.pos1 < r.pos0, igualp = r.pos1 === r.pos0;
  const posTxt = igualp ? `posição ${nf1.format(r.pos0)}, igual` : `posição ${nf1.format(r.pos0)} → ${nf1.format(r.pos1)}`;
  return `<div class="row">
    <div class="nm">${o.titulo_depois.split(':')[0]}<small>${o.balde} · ${o.slug.length > 38 ? o.slug.slice(0,38)+'…' : o.slug}</small></div>
    <div class="pair" role="img" aria-label="${o.titulo_depois.split(':')[0]}: impressões de ${r.imp0} para ${r.imp1}">
      <div class="bar a"><div class="track"><i style="width:${r.imp0/max*100}%"></i></div><span>${nf.format(r.imp0)}</span></div>
      <div class="bar d"><div class="track"><i style="width:${r.imp1/max*100}%"></i></div><span>${nf.format(r.imp1)}</span></div>
    </div>
    <div class="delta"><b>+${r.var}%</b><span class="${!melhor && !igualp ? 'pos-pior' : ''}">${posTxt}</span></div>
  </div>`;
}).join('');

document.getElementById('leitura').innerHTML = [
  ['Janela curta', `São ${S41[0].res.janela} dias de dado depois da reescrita. A leitura firme vem na medição de 28 dias.`],
  ['Impressão ainda não é clique', 'Nenhum dos 5 artigos tinha 10 cliques antes, então a medição usou impressões. Cliques e leads são o próximo teste.'],
  [`Posição: ${desceu} artigos desceram`, 'Quando o artigo passa a aparecer em mais buscas, as novas costumam entrar em posições mais baixas e a média cai, mesmo com mais gente vendo.'],
  ['Sem grupo de controle', 'Parte da alta pode ser sazonalidade. A medição compara o mesmo artigo antes e depois, não contra um artigo parado.'],
].map(([t,p]) => `<div class="leit"><span class="big">${t}</span><p>${p}</p></div>`).join('');

/* ciclo 2 */
document.getElementById('eb2').textContent = `Ciclo ${novo.ciclo} · no ar em ${dBR(novo.data)}`;
document.getElementById('sub-n').innerHTML = `Quatro artigos reescritos pelas regras da skill: 2.000 palavras ou mais, FAQ de 10 ou mais perguntas, fonte externa conferida, nenhum número sem origem. Cada um tem backup para reverter. A medição de 12 dias sai em ${D.medicao ? dBR(D.medicao) : 'breve'}.`;
const maxW = 3000;
document.getElementById('arts').innerHTML = NOVOS.map(o => {
  const a = o.auditoria;
  return `<article class="art">
    <div class="top2"><span class="chip"><i style="background:${o.balde==='Decadente'?'var(--bar-pior)':'var(--bar-depois)'}"></i>${o.balde}</span><span class="small">${o.motivo}</span></div>
    <div style="display:flex;flex-direction:column;gap:4px"><span class="novo">${o.titulo_depois}</span><span class="velho">${o.titulo_antes}</span></div>
    <div class="mets">
      <div class="met"><span class="k">Palavras</span><span class="val"><s>${nf.format(a.antes.palavras)}</s> ${nf.format(a.depois.palavras)}</span></div>
      <div class="met"><span class="k">Apontamentos</span><span class="val"><s>${a.antes.falhas}</s> ${a.depois.falhas}</span></div>
      <div class="met"><span class="k">Perguntas no FAQ</span><span class="val">${o.faq ?? '-'}</span></div>
    </div>
    <div class="words">
      <div class="wr"><span>Antes</span><div class="track"><i style="width:${a.antes.palavras/maxW*100}%;background:var(--bar-antes)"></i><span class="goal" style="left:${2000/maxW*100}%"></span></div><span>${nf.format(a.antes.palavras)} pal.</span></div>
      <div class="wr"><span>Depois</span><div class="track"><i style="width:${a.depois.palavras/maxW*100}%;background:var(--bar-depois)"></i><span class="goal" style="left:${2000/maxW*100}%"></span></div><span>${nf.format(a.depois.palavras)} pal.</span></div>
      <span class="small">O traço marca o piso de 2.000 palavras da skill. Apontamentos são os itens que a auditoria reprovava.</span>
    </div>
    <p class="nota">${o.nota}</p>
    ${o.vigiar ? `<div class="vig"><b>Vigiar:</b> ${o.vigiar}</div>` : ''}
  </article>`;
}).join('');

/* calendário */
const ev = [
  {w: dBR(D.ciclos[0].data), t: `Ciclo ${D.ciclos[0].ciclo}: ${D.ciclos[0].n} artigos reescritos e publicados`, ok:true},
  {w: '22/10/2026', t: `Medição do primeiro ciclo: ${S41.length} de ${S41.length} melhoraram em impressões`, ok:true},
  {w: dBR(novo.data), t: `Ciclo ${novo.ciclo}: ${NOVOS.length} artigos reescritos e publicados`, ok:true},
];
if (D.medicao) ev.push({w: dBR(D.medicao), t: `Medição automática do ciclo ${novo.ciclo} (tarefa agendada, sem login) e início do ciclo seguinte`, ok:false});
ev.push({w: 'Depois de 28 dias', t: 'Leitura firme de cada artigo: cliques e leads, não só impressões. Quem foi otimizado volta a ser elegível.', ok:false});
document.getElementById('tl').innerHTML = ev.map(e => `<div class="ev ${e.ok?'ok':''}"><span class="w">${e.w}</span><span class="t">${e.t}</span></div>`).join('');

document.getElementById('foot').innerHTML = `<span>Fontes: Google Search Console (metakosmos.com.br), GA4, Payload CMS e o Log de Otimizações no Drive da mK.</span><span>Relatório gerado em ${D.gerado_em}. As medições comparam janelas de mesmo tamanho antes e depois da data de cada reescrita.</span>`;
})();
</script>
"""

if __name__ == "__main__":
    main()
