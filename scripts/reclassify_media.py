#!/usr/bin/env python3
"""
reclassify_media.py — Renomeia mídia já enviada ao Payload (prefixo de solução mK + alt melhor).

Payload não permite renomear o arquivo via PATCH simples (só troca o campo no banco,
quebra o link do storage — testado e confirmado). Pra renomear de verdade: baixa o
arquivo atual, APAGA o doc antigo, sobe de novo com o nome/alt novos.

Só usar em itens que ainda não estão referenciados em nenhum post (mídia recém-subida
por este pipeline, sem uso em conteúdo publicado).

Uso: edita MAPPING abaixo (old_id -> new_filename/new_alt) e roda:
    python scripts/reclassify_media.py
"""
import json
from pathlib import Path

import requests

SKILL = Path(__file__).resolve().parent.parent
ENV_FILE = SKILL / ".env"

MAPPING = {
    414: {
        "new_filename": "kapo-cabelo-cacheado-resultado-filtro-evento.webp",
        "new_alt": "Selfie de mulher com cabelo cacheado longo e volumoso, resultado de filtro de evento da marca Kapo",
    },
}


def load_env():
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def payload_login(env):
    api = env["PAYLOAD_API_URL"].rstrip("/")
    r = requests.post(f"{api}/api/users/login",
                       json={"email": env["PAYLOAD_EMAIL"], "password": env["PAYLOAD_PASSWORD"]}, timeout=30)
    r.raise_for_status()
    return {"scheme": "JWT", "token": r.json()["token"], "api": api}


def main():
    env = load_env()
    auth = payload_login(env)
    h = {"Authorization": f"{auth['scheme']} {auth['token']}"}
    ok, fail = 0, 0
    for old_id, spec in MAPPING.items():
        r = requests.get(f"{auth['api']}/api/media/{old_id}", headers=h, timeout=30)
        if r.status_code != 200:
            print(f"  [X] {old_id}: não encontrado (HTTP {r.status_code})")
            fail += 1
            continue
        doc = r.json()
        full_url = doc["url"] if doc["url"].startswith("http") else f"{auth['api']}{doc['url']}"
        raw = requests.get(full_url, timeout=60).content
        old_filename = doc["filename"]

        dresp = requests.delete(f"{auth['api']}/api/media/{old_id}", headers=h, timeout=30)
        if dresp.status_code not in (200, 201):
            print(f"  [X] {old_id}: falha ao apagar (HTTP {dresp.status_code}) {dresp.text[:150]}")
            fail += 1
            continue

        ext = spec["new_filename"].rsplit(".", 1)[-1]
        mime = {"webp": "image/webp", "gif": "image/gif", "png": "image/png", "jpg": "image/jpeg"}.get(ext, "application/octet-stream")
        files = {"file": (spec["new_filename"], raw, mime)}
        data = {"_payload": json.dumps({"alt": spec["new_alt"]}, ensure_ascii=False)}
        uresp = requests.post(f"{auth['api']}/api/media", headers=h, files=files, data=data, timeout=120)
        if uresp.status_code in (200, 201):
            new_doc = uresp.json().get("doc", uresp.json())
            print(f"  [OK] {old_id} ({old_filename}) apagado -> novo ID {new_doc.get('id')} ({spec['new_filename']})")
            ok += 1
        else:
            print(f"  [X] {old_id}: upload da versão renomeada falhou (HTTP {uresp.status_code}) {uresp.text[:200]}")
            fail += 1
    print(f"\nOK: {ok} reclassificados, {fail} falharam")


if __name__ == "__main__":
    main()
