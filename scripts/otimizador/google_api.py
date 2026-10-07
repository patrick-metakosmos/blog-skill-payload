# -*- coding: utf-8 -*-
"""Sessão autenticada nas APIs do Google com a conta de robô da mK.

A chave JSON da conta de robô fica FORA do git (caminho no .env, chave
GOOGLE_SA_KEY). O robô é usuário restrito no Search Console e leitor no GA4.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import SKILL_DIR, load_env  # noqa: E402

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import credentials as user_credentials
from google.oauth2 import service_account

ESCOPOS = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def sessao():
    env = load_env()
    caminho = env.get("GOOGLE_SA_KEY")
    if not caminho:
        sys.exit("[X] GOOGLE_SA_KEY ausente no .env (caminho da chave JSON da conta de robô)")
    chave = Path(caminho)
    if not chave.is_absolute():
        chave = SKILL_DIR / chave
    cred = service_account.Credentials.from_service_account_file(str(chave), scopes=ESCOPOS)
    return AuthorizedSession(cred), env


def sessao_gsc():
    """Plano B enquanto o proprietário do Search Console não adiciona o robô:
    se GSC_USER_CRED estiver no .env, lê o Search Console com o login do
    Patrick (acesso total, só leitura aqui). Para voltar ao robô, basta tirar
    a linha do .env."""
    s, env = sessao()
    caminho = env.get("GSC_USER_CRED")
    if not caminho:
        return s, env
    arq = Path(caminho)
    if not arq.is_absolute():
        arq = SKILL_DIR / arq
    cred = user_credentials.Credentials.from_authorized_user_file(str(arq)).with_quota_project(
        env.get("GCP_QUOTA_PROJECT", "mk-otimizador-blog"))
    return AuthorizedSession(cred), env


def checar(resp, contexto):
    if resp.status_code != 200:
        sys.exit(f"[X] {contexto}: HTTP {resp.status_code} {resp.text[:400]}")
    return resp.json()
