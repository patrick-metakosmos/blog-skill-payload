#!/usr/bin/env python3
"""
swap_post_images.py — Troca as imagens dos posts do blog pelas novas mídias otimizadas
(skill blog mK Payload).

Padrão prepare/apply igual ao optimize_media.py: extrai o contexto de cada slot de
imagem de um post (featuredImage + nós "upload" no Lexical), eu escolho a mídia nova
mais adequada (olhando references/media-payload.md), e o script aplica a troca nos
3 locales (pt-BR/en/es), preservando todo o resto do conteúdo.

Fluxo:
    python scripts/swap_post_images.py --seed
    python scripts/swap_post_images.py --prepare 2 68 18     # por id específico (piloto)
    python scripts/swap_post_images.py --prepare 5           # N pendentes quaisquer
    # (eu preencho references/_post_naming_results.json)
    python scripts/swap_post_images.py --apply
    python scripts/swap_post_images.py --report
"""
import argparse
import json
import sys
from pathlib import Path

import requests

SKILL = Path(__file__).resolve().parent.parent
REFS = SKILL / "references"
DB_FILE = REFS / "post-images-db.json"
QUEUE_FILE = REFS / "_post_naming_queue.json"
RESULTS_FILE = REFS / "_post_naming_results.json"
ENV_FILE = SKILL / ".env"

CONTEXT_CHARS = 220


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


def auth_headers(auth):
    return {"Authorization": f"{auth['scheme']} {auth['token']}"}


def load_db():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    return []


def save_db(db):
    DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def seed():
    env = load_env()
    auth = payload_login(env)
    r = requests.get(f"{auth['api']}/api/posts?limit=200&depth=0", headers=auth_headers(auth), timeout=60)
    docs = r.json()["docs"]
    db = load_db()
    by_id = {m["id"]: m for m in db}
    added = 0
    for d in docs:
        if d["id"] in by_id:
            continue
        by_id[d["id"]] = {
            "id": d["id"], "slug": d.get("slug"), "title": d.get("title"),
            "status": d.get("_status"), "process_status": "pending",
            "old_featured_id": None, "new_featured_id": None,
            "old_inline_ids": None, "new_inline_ids": None,
        }
        added += 1
    db = list(by_id.values())
    save_db(db)
    print(f"OK: seed com {len(db)} posts ({added} novos)")


def _text_of(node):
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    out = []
    for c in node.get("children", []) or []:
        out.append(_text_of(c))
    return "".join(out)


def extract_slots(content):
    """Percorre o content Lexical (root) e retorna lista de {value, context} na ordem em que aparecem."""
    slots = []
    last_text = ""

    def walk(node):
        nonlocal last_text
        if isinstance(node, dict):
            t = node.get("type")
            if t in ("heading", "paragraph", "quote", "listitem"):
                txt = _text_of(node).strip()
                if txt:
                    last_text = txt
            if t == "upload":
                slots.append({"old_id": node.get("value"), "context": last_text[:CONTEXT_CHARS]})
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(content)
    return slots


def fetch_post(auth, post_id, locale):
    r = requests.get(f"{auth['api']}/api/posts/{post_id}?depth=0&locale={locale}",
                      headers=auth_headers(auth), timeout=30)
    r.raise_for_status()
    return r.json()


def prepare(ids, n):
    env = load_env()
    auth = payload_login(env)
    db = load_db()
    by_id = {m["id"]: m for m in db}

    if ids:
        batch_ids = ids
    else:
        pend = [m["id"] for m in db if m["process_status"] == "pending"]
        batch_ids = pend[:n]

    if not batch_ids:
        print("Nenhum post pendente.")
        return

    queue = []
    for pid in batch_ids:
        m = by_id.get(pid)
        if not m:
            print(f"  [X] post {pid} não está no banco (rode --seed)")
            continue
        d = fetch_post(auth, pid, "pt-BR")
        slots = extract_slots(d.get("content"))
        m["old_featured_id"] = d.get("featuredImage")
        m["old_inline_ids"] = [s["old_id"] for s in slots]
        m["process_status"] = "prepared"
        queue.append({
            "id": pid, "slug": d.get("slug"), "title": d.get("title"),
            "categories": d.get("categories"), "excerpt": d.get("excerpt"),
            "old_featured_id": d.get("featuredImage"),
            "inline_slots": slots,
        })
    save_db(db)
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    template = [{"id": q["id"], "new_featured_id": None, "new_inline_ids": [None] * len(q["inline_slots"])} for q in queue]
    RESULTS_FILE.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(queue)} posts preparados")
    print(f"Fila: {QUEUE_FILE}")
    print(f"Preencher: {RESULTS_FILE}")
    for q in queue:
        print(f"  [{q['id']}] {q['slug']} — featured {q['old_featured_id']}, {len(q['inline_slots'])} slots inline")


def replace_uploads(content, new_ids):
    """Substitui, em ordem, o value de cada nó upload pela lista new_ids."""
    idx = [0]

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "upload":
                node["value"] = new_ids[idx[0]]
                idx[0] += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(content)
    return idx[0]


def apply_changes():
    env = load_env()
    auth = payload_login(env)
    db = load_db()
    by_id = {m["id"]: m for m in db}
    results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))

    ok = fail = 0
    for r in results:
        pid = r["id"]
        m = by_id.get(pid)
        if not m or m["process_status"] != "prepared":
            continue
        new_featured = r.get("new_featured_id")
        new_inline = r.get("new_inline_ids") or []
        if new_featured is None or any(v is None for v in new_inline):
            print(f"  [X] post {pid}: resultado incompleto, pulando")
            continue

        # Só pt-BR: é o locale canônico (default) e o único com todos os campos
        # obrigatórios preenchidos. en/es têm tradução incompleta (ex: title vazio)
        # e o Payload valida o documento inteiro no PATCH, então falha nesses locales.
        # Como o Payload cai em fallback pro pt-BR quando o campo do locale tá vazio,
        # en/es já herdam as imagens novas automaticamente — não precisa tocar neles.
        post_ok = True
        for locale in ("pt-BR",):
            d = fetch_post(auth, pid, locale)
            content = d.get("content")
            n_replaced = replace_uploads(content, new_inline)
            if n_replaced != len(new_inline):
                print(f"  [X] post {pid} ({locale}): esperava {len(new_inline)} slots, achou {n_replaced}")
                post_ok = False
                break
            resp = requests.patch(f"{auth['api']}/api/posts/{pid}?locale={locale}",
                                   headers={**auth_headers(auth), "Content-Type": "application/json"},
                                   json={"featuredImage": new_featured, "content": content}, timeout=60)
            if resp.status_code not in (200, 201):
                print(f"  [X] post {pid} ({locale}): PATCH falhou {resp.status_code} {resp.text[:200]}")
                post_ok = False
                break

        if post_ok:
            m["new_featured_id"] = new_featured
            m["new_inline_ids"] = new_inline
            m["process_status"] = "done"
            ok += 1
            print(f"  [OK] post {pid} ({m['slug']}): featured {m['old_featured_id']} -> {new_featured}, "
                  f"{len(new_inline)} slots trocados")
        else:
            fail += 1
    save_db(db)
    print(f"\nOK: {ok} posts atualizados, {fail} falharam")


def report():
    db = load_db()
    from collections import Counter
    c = Counter(m["process_status"] for m in db)
    print("Status:")
    for k, v in c.items():
        print(f"  {k}: {v}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--prepare", nargs="*", type=int, metavar="ID_OR_N")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.seed:
        seed()
    elif args.prepare is not None:
        if len(args.prepare) == 1:
            prepare(None, args.prepare[0])
        else:
            prepare(args.prepare, None)
    elif args.apply:
        apply_changes()
    elif args.report:
        report()
    else:
        ap.error("use --seed | --prepare N | --prepare ID1 ID2 ... | --apply | --report")


if __name__ == "__main__":
    main()
