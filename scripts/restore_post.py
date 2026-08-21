#!/usr/bin/env python3
"""
restore_post.py — Restaura post(s) do Payload a partir de um backup (backup_all_posts.py).
Reverte content, title, excerpt e seo para o estado salvo, AO VIVO (published).

Uso:
  python scripts/restore_post.py <backup_dir_name> all     # restaura todos
  python scripts/restore_post.py <backup_dir_name> 35      # restaura só o post 35
  python scripts/restore_post.py <backup_dir_name> 35 --dry # mostra o que faria
"""
import json, sys, urllib.request
from pathlib import Path

SK=Path(__file__).resolve().parent.parent
ENV={}
for l in (SK/".env").read_text(encoding="utf-8").splitlines():
    l=l.strip()
    if l and not l.startswith("#") and "=" in l:
        k,v=l.split("=",1); ENV[k.strip()]=v.strip()
API=ENV["PAYLOAD_API_URL"].rstrip("/")

def http(m,u,b=None,t=None):
    h={"Accept":"application/json","User-Agent":"restore/1"}
    if t: h["Authorization"]=f"JWT {t}"
    if isinstance(b,(dict,list)): b=json.dumps(b,ensure_ascii=False).encode("utf-8"); h["Content-Type"]="application/json; charset=utf-8"
    with urllib.request.urlopen(urllib.request.Request(u,data=b,method=m,headers=h),timeout=90) as r:
        d=r.read().decode(); return json.loads(d) if d else {}

def main():
    if len(sys.argv)<3:
        print("uso: restore_post.py <backup_dir> <id|all> [--dry]"); return
    bdir=SK/"backups"/sys.argv[1]
    target=sys.argv[2]; dry="--dry" in sys.argv
    man=json.loads((bdir/"manifest.json").read_text(encoding="utf-8"))
    tok=http("POST",f"{API}/api/users/login",b={"email":ENV["PAYLOAD_EMAIL"],"password":ENV["PAYLOAD_PASSWORD"]})["token"]
    posts=man["posts"] if target=="all" else [p for p in man["posts"] if str(p["id"])==str(target)]
    if not posts: print(f"post {target} não está no backup"); return
    for p in posts:
        pid=p["id"]
        for loc,fn in p["locales"].items():
            doc=json.loads((bdir/fn).read_text(encoding="utf-8"))
            body={k:doc[k] for k in ("title","excerpt","content","seo") if k in doc and doc[k] is not None}
            if dry:
                print(f"[dry] restauraria post {pid} [{loc}] ({len(json.dumps(body))} bytes)"); continue
            http("PATCH", f"{API}/api/posts/{pid}?locale={loc}", b=body, t=tok)
            print(f"restaurado post {pid} [{loc}]")
    print("OK")

if __name__=="__main__":
    main()
