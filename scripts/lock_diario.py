#!/usr/bin/env python3
"""
lock_diario.py — trava distribuída do artigo diário, para o trigger rodar em mais
de uma máquina sem gerar dois artigos no mesmo dia.

Como trava: o `git push` do arquivo `locks/<AAAA-MM-DD>.json` é atômico no GitHub.
Duas máquinas podem tentar ao mesmo tempo; só uma consegue o push, e a outra leva
rejeição de non-fast-forward e desiste. Antes disso ainda há um cinto de segurança:
se o Payload já tem post criado hoje, ninguém roda (cobre o caso de alguém ter
escrito o artigo do dia à mão).

Uso (dentro do artigo_diario.cmd):
    python scripts/lock_diario.py --acquire      # exit 0 = pode rodar, 1 = já feito/perdeu
    python scripts/lock_diario.py --finish --status done --slug <slug> --url <url>
      (com --status done, ja commita o backlog atualizado via commit_listas.py)
    python scripts/lock_diario.py --show         # só mostra o estado de hoje

Opções úteis:
    --stale-hours N   assume lock abandonado por outra máquina depois de N horas (default 3)
    --force           ignora a trava (uso manual, quando você quer um segundo artigo no dia)
"""
import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
LOCKS = SKILL / "locks"
sys.path.insert(0, str(SKILL / "scripts"))
from payload_publish import load_env, http, payload_login  # noqa: E402


def git(*args, check=False):
    r = subprocess.run(["git", "-C", str(SKILL), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falhou: {r.stderr.strip()[:300]}")
    return r


def hoje():
    return datetime.now().strftime("%Y-%m-%d")


def lock_path(dia=None):
    return LOCKS / f"{dia or hoje()}.json"


def maquina():
    return f"{socket.gethostname()} ({os.environ.get('USERNAME') or platform.node()})"


def ler_lock_remoto(dia=None):
    """Lê o lock do dia como está no origin/main, sem mexer na árvore local."""
    git("fetch", "origin", "main", "--quiet")
    rel = f"locks/{dia or hoje()}.json"
    r = git("show", f"origin/main:{rel}")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"status": "ilegivel"}


def post_criado_hoje(auth):
    """Cinto de segurança: alguém já criou post hoje (pelo pipeline ou à mão)?"""
    # com offset explícito: o Payload guarda UTC e, sem timezone, meia-noite local
    # viraria 21h do dia anterior — o que faria um post da noite passada contar como de hoje.
    inicio = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    q = urllib.parse.quote(inicio.isoformat())
    url = (f"{auth['api']}/api/posts?where[createdAt][greater_than_equal]={q}"
           f"&limit=5&depth=0&sort=-createdAt")
    code, r = http("GET", url, token=auth["token"], scheme=auth["scheme"])
    if code != 200:
        print(f"[!] nao consegui conferir posts de hoje (HTTP {code}); seguindo pela trava do git")
        return []
    return [(d.get("id"), d.get("slug"), d.get("_status")) for d in r.get("docs", [])]


def puxar(*extra):
    """pull --rebase com autostash: o trabalho local em andamento de quem estiver
    nesta máquina é guardado e devolvido, nunca descartado."""
    return git("-c", "rebase.autoStash=true", "pull", "--rebase", "origin", "main", *extra)


def escrever_e_pushar(dados, mensagem):
    LOCKS.mkdir(exist_ok=True)
    p = lock_path()
    rel = f"locks/{p.name}"
    antes = git("rev-parse", "HEAD").stdout.strip()
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    git("add", "--", rel, check=True)
    r = git("commit", "-m", mensagem, "--", rel)
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        raise RuntimeError(f"commit do lock falhou: {(r.stdout + r.stderr)[:300]}")
    push = git("push", "origin", "main")
    if push.returncode == 0:
        return True, (push.stdout + push.stderr).strip()

    # Perdemos a corrida. Desfaz SÓ o nosso commit e SÓ o arquivo de lock.
    # Nada de reset --hard aqui: a árvore de trabalho pode ter artigo em
    # andamento de quem usa esta máquina.
    if antes:
        git("reset", "--soft", antes)
    git("restore", "--staged", "--", rel)
    if git("cat-file", "-e", f"HEAD:{rel}").returncode == 0:
        git("checkout", "--", rel)   # o lock já era versionado: volta como estava
    else:
        p.unlink(missing_ok=True)    # o arquivo era nosso, criado agora
    puxar()
    return False, (push.stdout + push.stderr).strip()


def acquire(args):
    # 0) alinhar com o remoto antes de qualquer coisa
    git("fetch", "origin", "main", "--quiet")
    atras = git("rev-list", "--count", "HEAD..origin/main").stdout.strip()
    if atras and atras != "0":
        r = puxar()
        if r.returncode != 0:
            print("[X] nao consegui alinhar com o origin (rebase falhou). Resolva a mao:")
            print((r.stdout + r.stderr)[:500])
            return 1

    if args.force:
        print("[!] --force: ignorando a trava")
    else:
        # 1) alguem ja tem o lock de hoje?
        atual = ler_lock_remoto()
        if atual:
            st = atual.get("status")
            quem = atual.get("maquina", "?")
            if st == "done":
                print(f"[=] artigo de hoje ja foi feito por {quem}: {atual.get('slug')} -> {atual.get('url')}")
                return 1
            if st == "running":
                inicio = atual.get("inicio")
                velho = False
                if inicio:
                    try:
                        velho = datetime.fromisoformat(inicio) < datetime.now() - timedelta(hours=args.stale_hours)
                    except ValueError:
                        pass
                if not velho:
                    print(f"[=] {quem} esta rodando o artigo de hoje agora (desde {inicio}). Saindo.")
                    return 1
                print(f"[!] lock de {quem} parado ha mais de {args.stale_hours}h; assumindo.")
            elif st == "failed":
                print(f"[!] tentativa de {quem} falhou hoje; assumindo para tentar de novo.")

        # 2) cinto de seguranca: post ja criado hoje no Payload
        criados = post_criado_hoje(payload_login(load_env()))
        if criados:
            print(f"[=] o Payload ja tem post criado hoje ({criados[0][1]}). Nao vou gerar outro.")
            return 1

    # 3) tenta cravar o lock. Quem conseguir o push, roda.
    dados = {
        "dia": hoje(),
        "status": "running",
        "maquina": maquina(),
        "inicio": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        ok, saida = escrever_e_pushar(dados, f"lock: artigo diario {hoje()} ({maquina()})")
    except RuntimeError as e:
        print(f"[X] {e}")
        return 1
    if not ok:
        print("[=] outra maquina cravou o lock primeiro (push rejeitado). Saindo.")
        return 1
    print(f"[OK] lock de {hoje()} adquirido por {maquina()}. Pode gerar o artigo.")
    return 0


def finish(args):
    git("fetch", "origin", "main", "--quiet")
    puxar()
    atual = ler_lock_remoto() or {"dia": hoje(), "maquina": maquina()}
    atual.update({
        "status": args.status,
        "fim": datetime.now().isoformat(timespec="seconds"),
        "maquina": atual.get("maquina") or maquina(),
    })
    if args.slug:
        atual["slug"] = args.slug
    if args.url:
        atual["url"] = args.url
    if args.nota:
        atual["nota"] = args.nota
    try:
        ok, saida = escrever_e_pushar(atual, f"lock: artigo diario {hoje()} -> {args.status}")
    except RuntimeError as e:
        print(f"[X] {e}")
        return 1
    if not ok:
        print(f"[!] nao consegui publicar o resultado do lock: {saida[:200]}")
        return 1
    print(f"[OK] lock de hoje marcado como '{args.status}'")

    # Artigo no ar: manda o backlog atualizado junto, para a outra maquina nao
    # reescrever a mesma pauta amanha. Import local: commit_listas importa daqui.
    if args.status == "done" and not args.sem_listas:
        import commit_listas
        sys.argv = ["commit_listas.py"] + (["--slug", args.slug] if args.slug else [])
        rc = commit_listas.main()
        if rc != 0:
            print("[!] o lock foi gravado, mas as listas nao subiram. Rode:")
            print("    python scripts/commit_listas.py --slug <slug>")
    return 0


def mostrar(args):
    atual = ler_lock_remoto(args.dia)
    print(f"lock {args.dia or hoje()}: {json.dumps(atual, ensure_ascii=False) if atual else 'nao existe (ninguem rodou)'}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acquire", action="store_true")
    ap.add_argument("--finish", action="store_true")
    ap.add_argument("--status", default=None, help="com --finish: done|failed")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--url", default=None)
    ap.add_argument("--nota", default=None)
    ap.add_argument("--show", action="store_true", help="mostra o lock do dia e sai")
    ap.add_argument("--dia", default=None)
    ap.add_argument("--stale-hours", type=float, default=3.0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sem-listas", action="store_true",
                    help="com --finish: nao commitar o backlog junto")
    a = ap.parse_args()
    if a.acquire:
        return acquire(a)
    if a.finish:
        if a.status not in ("done", "failed"):
            ap.error("--finish exige --status done|failed")
        return finish(a)
    return mostrar(a)


if __name__ == "__main__":
    sys.exit(main())
