#!/usr/bin/env python3
"""
backup_all_posts.py — Backup completo de TODOS os posts do Payload (rede de segurança
antes do rollout de revisões). Salva o doc inteiro de cada post, nos 3 locales,
em backups/full_<timestamp>/. Gera manifest.json.

Uso: python scripts/backup_all_posts.py
Restaurar: python scripts/restore_post.py <backup_dir> <id|all>
"""
import json, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
ENV = {}
for l in (SK/".env").read_text(encoding="utf-8").splitlines():
    l=l.strip()
    if l and not l.startswith("#") and "=" in l:
        k,v=l.split("=",1); ENV[k.strip()]=v.strip()
API=ENV["PAYLOAD_API_URL"].rstrip("/")
LOCALES=["pt-BR","en","es"]

def http(m,u,b=None,t=None):
    h={"Accept":"application/json","User-Agent":"backup/1"}
    if t: h["Authorization"]=f"JWT {t}"
    if isinstance(b,(dict,list)): b=json.dumps(b).encode(); h["Content-Type"]="application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(u,data=b,method=m,headers=h),timeout=90) as r:
            d=r.read().decode(); return r.status,(json.loads(d) if d else {})
    except urllib.error.HTTPError as e:
        return e.code, {}

tok=http("POST",f"{API}/api/users/login",b={"email":ENV["PAYLOAD_EMAIL"],"password":ENV["PAYLOAD_PASSWORD"]})[1]["token"]

# lista todos os ids
ids=[]; page=1
while True:
    _,r=http("GET",f"{API}/api/posts?limit=100&page={page}&depth=0&draft=false&locale=pt-BR",t=tok)
    for d in r.get("docs",[]): ids.append((d["id"], d.get("slug")))
    if not r.get("hasNextPage"): break
    page+=1

stamp=datetime.now().strftime("%Y%m%d_%H%M")
bdir=SK/"backups"/f"full_{stamp}"; bdir.mkdir(parents=True, exist_ok=True)
manifest={"timestamp":stamp,"api":API,"locales":LOCALES,"posts":[]}
ok=0
for pid,slug in ids:
    entry={"id":pid,"slug":slug,"locales":{}}
    for loc in LOCALES:
        code,doc=http("GET",f"{API}/api/posts/{pid}?depth=0&draft=false&locale={loc}",t=tok)
        if code==200 and doc:
            fn=f"post_{pid}_{loc}.json"
            (bdir/fn).write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
            entry["locales"][loc]=fn; ok+=1
    manifest["posts"].append(entry)
    print(f"  backup post {pid} ({slug}) — {len(entry['locales'])} locales")
(bdir/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"\nOK: {len(ids)} posts, {ok} arquivos de locale -> {bdir}")
print(f"Restaurar tudo:      python scripts/restore_post.py \"{bdir.name}\" all")
print(f"Restaurar um post:   python scripts/restore_post.py \"{bdir.name}\" <id>")
