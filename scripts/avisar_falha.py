# -*- coding: utf-8 -*-
"""Avisa no #only-marketing (bot "Mega Brain mK") quando a tarefa agendada do blog falha.

Criado em 24/11/2026: em 23/11 o artigo diário falhou às 07:00 e às 11:00 (login do Claude
expirado) e ninguém soube até o Mega Brain acusar atraso no dia seguinte.

Chamado pelos .cmd das tarefas, só quando a tentativa falhou:
    python scripts/avisar_falha.py artigo     <log> <exit>
    python scripts/avisar_falha.py otimizador <log> <exit>
O link do webhook fica no .env (SLACK_WEBHOOK_MEGABRAIN), nunca no log nem na mensagem.
"""
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

MOTIVOS = [  # (trecho do log, explicação para o time)
    ("OAuth session expired", "o login do Claude no PC expirou. Abra um terminal, rode `claude` e entre de novo"),
    ("Failed to authenticate", "o Claude no PC não conseguiu autenticar. Rode `claude` num terminal e entre de novo"),
    ("Not logged in", "o Claude no PC está deslogado. Rode `claude` num terminal e entre"),
    ("usage limit", "o limite de uso da assinatura do Claude acabou por agora"),
    ("rate limit", "o Claude recusou por limite de uso (rate limit)"),
    ("Token obtido", None),  # linha normal: não é motivo
]


def env(nome):
    for linha in (BASE / ".env").read_text(encoding="utf-8-sig").splitlines():
        if linha.strip().startswith(nome + "="):
            return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def ultima_tentativa(log):
    try:
        texto = Path(log).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return texto.rsplit("INICIO", 1)[-1]


def motivo(trecho):
    for chave, explicacao in MOTIVOS:
        if explicacao and chave.lower() in trecho.lower():
            return explicacao
    linhas = [l.strip() for l in trecho.splitlines()
              if l.strip() and not l.startswith("=") and "hooks.slack.com" not in l]
    fim = " | ".join(linhas[-3:])[:300]
    return f"erro não reconhecido; últimas linhas do log: {fim}" if fim else "erro sem detalhe no log"


def main():
    tarefa, log, rc = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "?"
    agora = datetime.now()
    por_que = motivo(ultima_tentativa(log))
    if tarefa == "artigo":
        proxima = ("Nova tentativa automática às 11:00." if agora.hour < 11
                   else "Não há nova tentativa hoje: o artigo de hoje fica faltando se ninguém rodar à mão.")
        texto = (f":red_circle: *Blog mK · artigo diário falhou* ({agora:%d/%m %H:%M}, exit {rc}): {por_que}. {proxima}")
    else:
        texto = (f":red_circle: *Otimizador do blog falhou* ({agora:%d/%m %H:%M}, exit {rc}): {por_que}. "
                 "O ciclo fica sem rodar até alguém disparar a tarefa de novo.")
    url = env("SLACK_WEBHOOK_MEGABRAIN")
    if not url:
        print("[!] sem SLACK_WEBHOOK_MEGABRAIN no .env: aviso não enviado")
        return
    req = urllib.request.Request(url, data=json.dumps({"text": texto}, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"[OK] aviso de falha enviado ao Slack ({r.read().decode()[:20]})")
    except Exception as e:  # noqa: BLE001 - o aviso nunca pode derrubar a tarefa
        print(f"[!] aviso de falha não enviado: {type(e).__name__}")


if __name__ == "__main__":
    main()
