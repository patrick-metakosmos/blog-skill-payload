#!/usr/bin/env python3
"""Health-check de todos os posts: status, blocos, caixas, toggle, R$, negrito, categoria."""
import sys, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
SK = Path(__file__).resolve().parent.parent
ENV = {}
for l in (SK/".env").read_text(encoding="utf-8").splitlines():
    l=l.strip()
    if l and not l.startswith("#") and "=" in l:
        k,v=l.split("=",1); ENV[k.strip()]=v.strip()
API=ENV["PAYLOAD_API_URL"].rstrip("/")
def http(m,u,t=None):
    h={"Accept":"application/json","User-Agent":"v/1"}
    if t: h["Authorization"]=f"JWT {t}"
    with urllib.request.urlopen(urllib.request.Request(u,method=m,headers=h),timeout=60) as r:
        return json.loads(r.read().decode())
def post(u,b):
    h={"Accept":"application/json","Content-Type":"application/json","User-Agent":"v/1"}
    d=json.dumps(b).encode()
    with urllib.request.urlopen(urllib.request.Request(u,data=d,method="POST",headers=h),timeout=60) as r:
        return json.loads(r.read().decode())
tok=post(f"{API}/api/users/login",{"email":ENV["PAYLOAD_EMAIL"],"password":ENV["PAYLOAD_PASSWORD"]})["token"]
lst=http("GET",f"{API}/api/posts?limit=200&depth=1&draft=false&locale=pt-BR&sort=id",tok)
print(f"{'id':>3} {'st':<4} {'blk':>4} {'quo':>3} {'neg':>3} {'tog':>3} {'R$':>3} {'cat':<22} slug")
import re
for d in lst["docs"]:
    raw=json.dumps(d.get("content"),ensure_ascii=False)
    blk=len((d.get("content") or {}).get("root",{}).get("children",[]))
    quo=len(re.findall(r'"type":\s*"quote"',raw))
    neg=len(re.findall(r'"format":\s*1,',raw))+len(re.findall(r'"format":\s*9,',raw))
    tog="SIM" if re.search(r'"text":\s*"(Conteúdo|Toggle)"',raw) else "-"
    money=len(re.findall(r'R\$\s?\d',raw))
    cats=",".join([c.get("title","?")[:20] for c in (d.get("categories") or []) if isinstance(c,dict)]) or "SEM CAT"
    st=d.get("_status","?")[:4]
    print(f"{d['id']:>3} {st:<4} {blk:>4} {quo:>3} {neg:>3} {tog:>3} {money:>3} {cats:<22} {d.get('slug')}")
