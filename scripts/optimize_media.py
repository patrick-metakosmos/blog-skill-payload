#!/usr/bin/env python3
"""
optimize_media.py — Otimiza e rebatiza a Media do Payload (skill blog mK Payload)

A Media do Payload (herdada do WP) tem nomes de arquivo sem sentido e alts fracos.
Este script baixa cada mídia, otimiza (resize + recompressão pra ~2MB) e sobe uma
CÓPIA NOVA no Payload com nome de arquivo e alt melhores — a mídia antiga NUNCA é
tocada/apagada, então nenhum post existente quebra.

A parte mecânica (download, resize, compressão, upload) é 100% deste script.
A parte de nome/alt exige visão humana/IA: eu (Claude) vejo os arquivos otimizados
com o Read tool numa sessão e preencho _naming_results.json.

Fluxo:
    python scripts/optimize_media.py --seed                # popula o banco (1x)
    python scripts/optimize_media.py --prepare 20           # baixa+otimiza um lote
    # (eu vejo os arquivos em references/_optimize_work/ e preencho _naming_results.json)
    python scripts/optimize_media.py --apply-names          # renomeia local
    python scripts/optimize_media.py --upload                # sobe no Payload
    python scripts/optimize_media.py --report                # progresso

Uso: python scripts/sync_payload_media.py PRECISA rodar antes do --seed (gera media-payload.json).
"""
import argparse
import io
import json
from collections import Counter
from pathlib import Path

import requests
from PIL import Image, ImageSequence

SKILL = Path(__file__).resolve().parent.parent
REFS = SKILL / "references"
WORK = REFS / "_optimize_work"
DB_FILE = REFS / "media-optimize-db.json"
QUEUE_FILE = REFS / "_naming_queue.json"
RESULTS_FILE = REFS / "_naming_results.json"
MEDIA_JSON = REFS / "media-payload.json"
ENV_FILE = SKILL / ".env"

MAX_DIM = 2000
TARGET_BYTES = 2 * 1024 * 1024
MIN_QUALITY = 50
SMALL_ORIGINAL_BYTES = 300 * 1024  # abaixo disso, provável logo/ícone: não vale a pena perder qualidade
SKIP_MIME = {"image/svg+xml", "application/pdf"}
EXT_MIME = {".webp": "image/webp", ".gif": "image/gif", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".png": "image/png"}


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
    coll = env.get("PAYLOAD_AUTH_COLLECTION", "users")
    if env.get("PAYLOAD_API_KEY"):
        return {"scheme": f"{coll} API-Key", "token": env["PAYLOAD_API_KEY"], "api": api}
    r = requests.post(f"{api}/api/{coll}/login",
                       json={"email": env["PAYLOAD_EMAIL"], "password": env["PAYLOAD_PASSWORD"]},
                       timeout=30)
    r.raise_for_status()
    token = r.json()["token"]
    return {"scheme": env.get("PAYLOAD_AUTH_SCHEME", "JWT"), "token": token, "api": api}


def load_db():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    return []


def save_db(db):
    DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def seed():
    media = json.loads(MEDIA_JSON.read_text(encoding="utf-8"))
    db = load_db()
    by_id = {m["id"]: m for m in db}
    added = 0
    for it in media:
        if it["id"] in by_id:
            continue
        by_id[it["id"]] = {
            "id": it["id"], "old_filename": it["filename"], "old_alt": it.get("alt", ""),
            "old_size": it.get("filesize"), "mime": it.get("mime"), "url": it.get("url"),
            "width": it.get("width"), "height": it.get("height"),
            "status": "pending", "skip_reason": None, "optimize_note": None,
            "new_filename": None, "new_alt": None,
            "optimized_size": None, "new_media_id": None,
            "_local_ext": None, "_local_path": None,
        }
        added += 1
    db = list(by_id.values())
    save_db(db)
    print(f"OK: seed com {len(db)} itens ({added} novos)")


def optimize_image_bytes(raw, mime):
    """Retorna (bytes_otimizados, ext, aviso_ou_None) ou (None, None, motivo_skip)."""
    if mime in SKIP_MIME:
        return None, None, "formato não otimizável"
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        return None, None, f"erro ao abrir: {e}"

    if getattr(im, "is_animated", False):
        w, h = im.size
        anim_max = min(MAX_DIM, 1400)  # GIF grande costuma pesar por causa das dimensões/frames, não só qualidade
        durations = [f.info.get("duration", 100) for f in ImageSequence.Iterator(im)]
        if max(w, h) > anim_max:
            scale = anim_max / max(w, h)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            frames = [f.convert("RGBA").resize(new_size, Image.LANCZOS) for f in ImageSequence.Iterator(im)]
        else:
            frames = [f.convert("RGBA") for f in ImageSequence.Iterator(im)]

        # GIF (paleta 256 cores) é péssimo pra animações longas/gradiente — WebP animado
        # comprime MUITO melhor mantendo qualidade visual. Convertido pra .webp.
        quality = 80
        buf = None
        while True:
            b = io.BytesIO()
            frames[0].save(b, format="WEBP", save_all=True, append_images=frames[1:],
                            duration=durations, loop=im.info.get("loop", 0),
                            quality=quality, method=6)
            buf = b
            if b.tell() <= TARGET_BYTES or quality <= 35:
                break
            quality = max(35, quality - 15)
        note = f"GIF animado ({len(frames)} frames) convertido pra WebP animado"
        if len(raw) and buf.tell() >= len(raw):
            # WebP não ajudou (raro) — mantém GIF original redimensionado só se precisar
            if max(w, h) > anim_max:
                gb = io.BytesIO()
                frames[0].convert("P", palette=Image.ADAPTIVE).save(
                    gb, format="GIF", save_all=True,
                    append_images=[f.convert("P", palette=Image.ADAPTIVE) for f in frames[1:]],
                    duration=durations, loop=im.info.get("loop", 0), disposal=2)
                return gb.getvalue(), "gif", "WebP não reduziu o tamanho; GIF redimensionado mantido"
            return raw, "gif", "WebP não reduziu o tamanho; GIF original mantido como está"
        return buf.getvalue(), "webp", note

    w, h = im.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA") if has_alpha else im.convert("RGB")

    if len(raw) < SMALL_ORIGINAL_BYTES:
        # provável logo/ícone: preserva nitidez de bordas/texto, sem compressão com perda
        buf = io.BytesIO()
        im.save(buf, format="WEBP", lossless=True, quality=100, method=6)
        return buf.getvalue(), "webp", "arquivo pequeno (provável logo/ícone) — convertido pra WebP sem perda"

    quality = 85
    buf = None
    while True:
        b = io.BytesIO()
        im.save(b, format="WEBP", quality=quality, method=6)
        buf = b
        if b.tell() <= TARGET_BYTES or quality <= MIN_QUALITY:
            break
        quality = max(MIN_QUALITY, quality - 10)
    return buf.getvalue(), "webp", None


def prepare(n):
    env = load_env()
    base = env["PAYLOAD_API_URL"].rstrip("/")
    db = load_db()
    pend = [m for m in db if m["status"] == "pending"]
    pend.sort(key=lambda m: -(m.get("old_size") or 0))
    batch = pend[:n]
    if not batch:
        print("Nenhum item pendente.")
        return
    WORK.mkdir(exist_ok=True)
    queue = []
    for m in batch:
        full_url = m["url"] if m["url"].startswith("http") else f"{base}{m['url']}"
        try:
            r = requests.get(full_url, timeout=60)
            r.raise_for_status()
            raw = r.content
        except Exception as e:
            m["status"], m["skip_reason"] = "skipped", f"download falhou: {e}"
            continue
        opt, ext, note = optimize_image_bytes(raw, m.get("mime"))
        if opt is None:
            m["status"], m["skip_reason"] = "skipped", note
            continue
        local = WORK / f"{m['id']}.{ext}"
        local.write_bytes(opt)
        m["status"] = "optimized"
        m["optimized_size"] = len(opt)
        m["_local_ext"] = ext
        m["optimize_note"] = note
        queue.append({
            "id": m["id"], "old_filename": m["old_filename"], "old_alt": m["old_alt"],
            "local_file": str(local), "width": m.get("width"), "height": m.get("height"),
            "old_size_kb": (m.get("old_size") or 0) // 1024, "optimized_size_kb": len(opt) // 1024,
            "note": note,
        })
    save_db(db)
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    template = [{"id": q["id"], "new_filename": "", "new_alt": ""} for q in queue]
    RESULTS_FILE.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(queue)} otimizadas em {WORK}")
    print(f"Fila: {QUEUE_FILE}")
    print(f"Preencher: {RESULTS_FILE}")
    for q in queue:
        tail = f"  [{q['note']}]" if q["note"] else ""
        print(f"  {q['local_file']}  ({q['old_filename']}, {q['old_size_kb']}KB -> {q['optimized_size_kb']}KB){tail}")


def apply_names():
    db = load_db()
    by_id = {m["id"]: m for m in db}
    results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    applied = 0
    for r in results:
        if not r.get("new_filename"):
            continue
        m = by_id.get(r["id"])
        if not m or m["status"] != "optimized":
            continue
        ext = m["_local_ext"]
        old_local = WORK / f"{m['id']}.{ext}"
        new_filename = r["new_filename"]
        if not new_filename.lower().endswith(f".{ext}"):
            new_filename = f"{Path(new_filename).stem}.{ext}"
        new_local = WORK / new_filename
        if not old_local.exists():
            print(f"  [X] arquivo otimizado sumiu pra id {m['id']} ({old_local})")
            continue
        old_local.rename(new_local)
        m["new_filename"] = new_filename
        m["new_alt"] = r.get("new_alt", "")
        m["status"] = "named"
        m["_local_path"] = str(new_local)
        applied += 1
    save_db(db)
    print(f"OK: {applied} itens renomeados e prontos pra upload")


def upload():
    env = load_env()
    auth = payload_login(env)
    db = load_db()
    ok = fail = 0
    for m in db:
        if m["status"] != "named":
            continue
        path = Path(m["_local_path"]) if m.get("_local_path") else (WORK / (m["new_filename"] or ""))
        if not path.exists():
            print(f"  [X] arquivo não encontrado pra id {m['id']}: {path}")
            fail += 1
            continue
        try:
            with open(path, "rb") as f:
                files = {"file": (m["new_filename"], f, EXT_MIME.get(path.suffix.lower(), "application/octet-stream"))}
                # Payload REST exige campos extras (fora do file) dentro de "_payload" (JSON stringificado)
                data = {"_payload": json.dumps({"alt": m["new_alt"] or ""}, ensure_ascii=False)}
                resp = requests.post(f"{auth['api']}/api/media",
                                      headers={"Authorization": f"{auth['scheme']} {auth['token']}"},
                                      files=files, data=data, timeout=120)
            if resp.status_code in (200, 201):
                doc = resp.json().get("doc", resp.json())
                m["new_media_id"] = doc.get("id")
                m["status"] = "uploaded"
                ok += 1
                print(f"  [OK] {m['old_filename']} -> {m['new_filename']} (novo ID {doc.get('id')})")
            else:
                print(f"  [X] upload falhou ({resp.status_code}) {m['new_filename']}: {resp.text[:200]}")
                fail += 1
        except Exception as e:
            print(f"  [X] erro no upload de {m['new_filename']}: {e}")
            fail += 1
    save_db(db)
    print(f"\nOK: {ok} enviados, {fail} falharam")


def report():
    db = load_db()
    c = Counter(m["status"] for m in db)
    total_old = sum((m.get("old_size") or 0) for m in db)
    total_new = sum((m.get("optimized_size") or 0) for m in db if m.get("optimized_size"))
    print("Status:")
    for k, v in c.items():
        print(f"  {k}: {v}")
    print(f"\nTamanho original total (todos os 348): {total_old // 1024} KB")
    if total_new:
        n_proc = sum(1 for m in db if m.get("optimized_size"))
        print(f"Tamanho otimizado ({n_proc} já processados): {total_new // 1024} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--prepare", type=int, metavar="N")
    ap.add_argument("--apply-names", action="store_true")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.seed:
        seed()
    elif args.prepare:
        prepare(args.prepare)
    elif args.apply_names:
        apply_names()
    elif args.upload:
        upload()
    elif args.report:
        report()
    else:
        ap.error("use --seed | --prepare N | --apply-names | --upload | --report")


if __name__ == "__main__":
    main()
