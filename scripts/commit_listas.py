#!/usr/bin/env python3
"""
commit_listas.py — depois de publicar um artigo, regenera as listas derivadas do
Payload e manda para o GitHub, para as duas máquinas verem o mesmo backlog.

O que entra no commit (só o que mudou de fato):
    Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md   <- status_backlog.py
    Pautas e Palavras Cahve/backlog.csv
    references/blog-links.md                       <- sync_payload_lists.py
    references/mkases.md
    references/media-payload.md                    <- só com --com-midia

Uso:
    python scripts/commit_listas.py --slug <slug>       # o normal, no fim da publicação
    python scripts/commit_listas.py                     # sem slug, mensagem genérica
    python scripts/commit_listas.py --com-midia         # se subiu mídia nova na sessão
    python scripts/commit_listas.py --dry-run           # regenera e mostra, não commita

Push rejeitado não vira conflito: como as listas são 100% derivadas do Payload, o
script se realinha com o remoto, REGENERA e commita de novo (até 3 tentativas).
Nunca faz reset --hard: artigo em andamento na máquina não é tocado.
"""
import argparse
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
from lock_diario import git, puxar  # noqa: E402

PASTA_PAUTAS = "Pautas e Palavras Cahve"
LISTAS = [
    f"{PASTA_PAUTAS}/BACKLOG-EDITORIAL.md",
    f"{PASTA_PAUTAS}/.BACKLOG-EDITORIAL.bak.md",
    f"{PASTA_PAUTAS}/backlog.csv",
    "references/blog-links.md",
    "references/mkases.md",
]
LISTA_MIDIA = "references/media-payload.md"


def rodar(script):
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / script)],
                       cwd=str(SKILL), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"[X] {script} falhou:\n{(r.stdout + r.stderr)[-500:]}")
        return None
    return r.stdout


def progresso(saida):
    """Pesca a linha de placar do status_backlog.py para a mensagem do commit."""
    for linha in (saida or "").splitlines():
        if linha.startswith("publicado:") or linha.startswith("progresso:"):
            return linha.strip()
    return ""


def regenerar(com_midia):
    saida = rodar("status_backlog.py")
    if saida is None:
        return None
    rodar("sync_payload_lists.py")
    if com_midia:
        rodar("sync_payload_media.py")
    return progresso(saida)


def mudou(paths):
    r = git("status", "--porcelain", "--", *paths)
    return [l for l in r.stdout.splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None)
    ap.add_argument("--com-midia", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tentativas", type=int, default=3)
    a = ap.parse_args()

    paths = list(LISTAS) + ([LISTA_MIDIA] if a.com_midia else [])

    for tentativa in range(1, a.tentativas + 1):
        # 1) partir sempre do estado mais novo do remoto
        git("fetch", "origin", "main", "--quiet")
        r = puxar()
        if r.returncode != 0:
            print("[X] nao consegui alinhar com o origin:")
            print((r.stdout + r.stderr)[:400])
            return 1

        # 2) regenerar as listas a partir do Payload
        placar = regenerar(a.com_midia)
        if placar is None:
            return 1

        alterados = mudou(paths)
        if not alterados:
            print(f"[=] listas ja estavam em dia ({placar or 'sem placar'}). Nada a commitar.")
            return 0

        print(f"[i] {len(alterados)} arquivo(s) de lista mudaram:")
        for l in alterados:
            print("   ", l)
        if a.dry_run:
            print("[=] --dry-run: nao commitei nada.")
            return 0

        # 3) commitar so as listas
        antes = git("rev-parse", "HEAD").stdout.strip()
        titulo = f"backlog: {a.slug} publicado" if a.slug else "backlog: listas atualizadas"
        msg = f"{titulo}\n\n{placar}" if placar else titulo
        git("add", "--", *paths, check=True)
        c = git("commit", "-m", msg, "--", *paths)
        if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
            print(f"[X] commit falhou: {(c.stdout + c.stderr)[:300]}")
            return 1

        push = git("push", "origin", "main")
        if push.returncode == 0:
            print(f"[OK] listas commitadas e enviadas. {placar}")
            return 0

        # 4) alguem pushou no meio. Desfaz SO o nosso commit e tenta de novo,
        #    regenerando: as listas saem do Payload, entao nunca ha conflito real.
        print(f"[!] push rejeitado (tentativa {tentativa}/{a.tentativas}); realinhando e refazendo.")
        if antes:
            git("reset", "--soft", antes)
        git("restore", "--staged", "--", *paths)

    print("[X] nao consegui enviar as listas depois de varias tentativas. Rode de novo mais tarde.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
