#!/usr/bin/env python3
"""
fix_migrated_posts.py — Limpa erros dos posts migrados no Payload.

Corrige (por regra, no campo content/Lexical):
  1. ToC/"toggle" migrado no corpo (parágrafo "Conteúdo", link "Toggle" url="#",
     lista de links-âncora) -> remove (o frontend gera o sumário sozinho).
  2. "Frase cortada destacada" = stat partido (parágrafo só com número tipo "+94%"
     seguido de parágrafo-legenda) -> vira UMA caixa <quote> com o número em negrito+sublinhado.
  3. Links internos sem UTM -> injeta utm_source=blog&utm_medium=internal-link&utm_content=<slug>
     (+ utm_campaign pelo pilar de destino quando identificável).

Uso:
  python scripts/fix_migrated_posts.py 35            # dry: mostra mudanças, salva cleaned, NÃO grava
  python scripts/fix_migrated_posts.py 35 --apply    # grava como RASCUNHO (draft) — não altera o publicado
"""
import json, re, sys, argparse, urllib.request
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
ENV = {}
for l in (SK/".env").read_text(encoding="utf-8").splitlines():
    l=l.strip()
    if l and not l.startswith("#") and "=" in l:
        k,v=l.split("=",1); ENV[k.strip()]=v.strip()
API=ENV["PAYLOAD_API_URL"].rstrip("/")

def http(m,u,b=None,t=None):
    h={"Accept":"application/json","User-Agent":"fix/1"}
    if t: h["Authorization"]=f"JWT {t}"
    if isinstance(b,(dict,list)): b=json.dumps(b,ensure_ascii=False).encode("utf-8"); h["Content-Type"]="application/json; charset=utf-8"
    with urllib.request.urlopen(urllib.request.Request(u,data=b,method=m,headers=h),timeout=90) as r:
        d=r.read().decode(); return json.loads(d) if d else {}

TOC_LABELS = {"conteúdo","conteudo","sumário","sumario","índice","indice","neste artigo"}
STAT_RE = re.compile(r"^[+\-]?\d[\d.,]*\s*(%|x|×|mi|mil|k|bi)?$", re.IGNORECASE)
PILAR_CAMPAIGN = {  # trecho do path de destino -> utm_campaign
    "provador": "pilar2-provador-virtual", "mk-fashion": "pilar2-provador-virtual",
    "visualizador-3d": "pilar3-visualizador-3d-ar", "mk3d": "pilar3-visualizador-3d-ar",
    "mk-3d-shop": "pilar3-visualizador-3d-ar", "3d-ar": "pilar3-visualizador-3d-ar",
    "immersive-commerce": "pilar1-immersive-commerce",
    "mkases": "pilar6-mkases-cases", "fooh": "pilar4-fooh-videos-ia",
}

def plaintext(n):
    out=[]
    def rec(x):
        if isinstance(x,dict):
            if x.get("type")=="text": out.append(x.get("text",""))
            for c in x.get("children",[]): rec(c)
        elif isinstance(x,list):
            for c in x: rec(c)
    rec(n); return "".join(out)

def para_links(n):
    return [c for c in n.get("children",[]) if isinstance(c,dict) and c.get("type")=="link"]
def only_links(n):
    kinds=[c.get("type") for c in n.get("children",[]) if not (c.get("type")=="text" and not c.get("text","").strip())]
    return bool(kinds) and all(k=="link" for k in kinds)

def is_toc(n):
    if n.get("type")!="paragraph": return False
    if plaintext(n).strip().lower() in TOC_LABELS: return True
    lk=para_links(n)
    if any((l.get("fields",{}) or {}).get("url","")=="#" for l in lk): return True
    if only_links(n) and lk and all("#" in ((l.get("fields",{}) or {}).get("url","")) for l in lk): return True
    return False

def txt(t,fmt=0): return {"mode":"normal","text":t,"type":"text","style":"","detail":0,"format":fmt,"version":1}
def quote(children): return {"type":"quote","format":"","indent":0,"version":1,"children":children,"direction":"ltr"}

def add_utm(url, slug):
    if "utm_" in url or "#" in url: return url, False
    low=url.lower(); camp="pilar-blog"
    for key,c in PILAR_CAMPAIGN.items():
        if key in low: camp=c; break
    sep="&" if "?" in url else "?"
    return f"{url}{sep}utm_source=blog&utm_medium=internal-link&utm_campaign={camp}&utm_content={slug}", True

def is_internal(u): return u.startswith("/") or "metakosmos.com.br" in u

def clean(children, slug, log):
    out=[]; i=0
    while i < len(children):
        n=children[i]
        # 1) ToC/toggle
        if is_toc(n):
            log["toc"]+=1; i+=1; continue
        # 2) stat partido -> quote
        if (n.get("type")=="paragraph" and STAT_RE.match(plaintext(n).strip())
                and i+1 < len(children) and children[i+1].get("type")=="paragraph"):
            stat=plaintext(n).strip()
            cap=children[i+1]
            qchildren=[txt(stat,1|8), txt(" ")]+cap.get("children",[])
            out.append(quote(qchildren)); log["stat"]+=1; i+=2; continue
        out.append(n); i+=1
    # 3) UTM em links (recursivo)
    def fix_links(x):
        if isinstance(x,dict):
            if x.get("type")=="link":
                f=x.get("fields",{}) or {}; u=f.get("url","")
                if is_internal(u):
                    nu,ch=add_utm(u,slug)
                    if ch: f["url"]=nu; x["fields"]=f; log["utm"]+=1
            for c in x.get("children",[]): fix_links(c)
        elif isinstance(x,list):
            for c in x: fix_links(c)
    for n in out: fix_links(n)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("pid", type=int)
    ap.add_argument("--apply", action="store_true", help="grava como RASCUNHO (draft)")
    args=ap.parse_args()
    tok=http("POST",f"{API}/api/users/login",b={"email":ENV["PAYLOAD_EMAIL"],"password":ENV["PAYLOAD_PASSWORD"]})["token"]
    p=http("GET",f"{API}/api/posts/{args.pid}?depth=0&draft=false&locale=pt-BR",t=tok)
    slug=p.get("slug","")
    root=(p.get("content") or {}).get("root") or {}
    ch=root.get("children",[])
    log={"toc":0,"stat":0,"utm":0}
    before=len(ch)
    newch=clean(ch, slug, log)
    root["children"]=newch
    content={"root":root}

    bdir=SK/"backups"; bdir.mkdir(exist_ok=True)
    (bdir/f"post{args.pid}_ptBR_cleaned.json").write_text(json.dumps(content,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"post {args.pid} ({slug})")
    print(f"  blocos: {before} -> {len(newch)}")
    print(f"  ToC/toggle removidos : {log['toc']}")
    print(f"  stats partidos -> caixa quote: {log['stat']}")
    print(f"  links sem UTM corrigidos: {log['utm']}")
    print(f"  cleaned salvo: backups/post{args.pid}_ptBR_cleaned.json")

    if not args.apply:
        print("\n(dry-run — nada gravado. Use --apply para gravar como RASCUNHO.)")
        return
    r=http("PATCH", f"{API}/api/posts/{args.pid}?locale=pt-BR&draft=true", b={"content":content}, t=tok)
    doc=r.get("doc", r)
    print(f"\n[OK] Gravado como RASCUNHO (draft). O post PUBLICADO ao vivo continua o antigo.")
    print(f"Revise no admin: {API}/admin/collections/posts/{args.pid}  (veja 'unpublished changes')")

if __name__=="__main__":
    main()
