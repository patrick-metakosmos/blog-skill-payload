#!/usr/bin/env python3
"""
local_upload_pipeline.py — Otimiza e sobe imagens LOCAIS novas pro Payload (skill blog mK Payload).

Variante de optimize_media.py pra quando as imagens não estão na Media do Payload ainda
(vieram de uma pasta local, ex: "novas imagens"). Mesmo padrão de nomenclatura e otimização.

Fluxo:
    python scripts/local_upload_pipeline.py --seed "novas imagens"   # popula o banco (1x)
    python scripts/local_upload_pipeline.py --prepare 15             # otimiza um lote
    # (eu vejo os arquivos em references/_local_work/ e preencho _local_naming_results.json)
    python scripts/local_upload_pipeline.py --apply-names
    python scripts/local_upload_pipeline.py --upload
    python scripts/local_upload_pipeline.py --report
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
WORK = REFS / "_local_work"
DB_FILE = REFS / "local-media-db.json"
QUEUE_FILE = REFS / "_local_naming_queue.json"
RESULTS_FILE = REFS / "_local_naming_results.json"
ENV_FILE = SKILL / ".env"

MAX_DIM = 2000
TARGET_BYTES = 2 * 1024 * 1024
MIN_QUALITY = 50
SMALL_ORIGINAL_BYTES = 300 * 1024
EXT_MIME = {".webp": "image/webp", ".gif": "image/gif", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".png": "image/png"}
SOURCE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


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


def load_db():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    return []


def save_db(db):
    DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def seed(source_dir):
    src = Path(source_dir)
    if not src.is_absolute():
        src = SKILL / source_dir
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in SOURCE_EXTS)
    db = load_db()
    by_path = {m["source_path"]: m for m in db}
    added = 0
    for i, p in enumerate(files):
        key = str(p)
        if key in by_path:
            continue
        by_path[key] = {
            "id": i, "source_path": key, "original_filename": p.name,
            "old_size": p.stat().st_size, "status": "pending",
            "skip_reason": None, "optimize_note": None,
            "new_filename": None, "new_alt": None,
            "optimized_size": None, "new_media_id": None,
            "_local_ext": None, "_local_path": None,
        }
        added += 1
    db = list(by_path.values())
    save_db(db)
    print(f"OK: seed com {len(db)} itens ({added} novos) de {src}")


def optimize_image_bytes(raw, mime):
    if mime in ("image/svg+xml", "application/pdf"):
        return None, None, "formato não otimizável"
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        return None, None, f"erro ao abrir: {e}"

    if getattr(im, "is_animated", False):
        w, h = im.size
        anim_max = min(MAX_DIM, 1400)
        durations = [f.info.get("duration", 100) for f in ImageSequence.Iterator(im)]
        if max(w, h) > anim_max:
            scale = anim_max / max(w, h)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            frames = [f.convert("RGBA").resize(new_size, Image.LANCZOS) for f in ImageSequence.Iterator(im)]
        else:
            frames = [f.convert("RGBA") for f in ImageSequence.Iterator(im)]
        quality = 80
        buf = None
        while True:
            b = io.BytesIO()
            frames[0].save(b, format="WEBP", save_all=True, append_images=frames[1:],
                            duration=durations, loop=im.info.get("loop", 0), quality=quality, method=6)
            buf = b
            if b.tell() <= TARGET_BYTES or quality <= 35:
                break
            quality = max(35, quality - 15)
        return buf.getvalue(), "webp", f"GIF animado ({len(frames)} frames) convertido pra WebP animado"

    w, h = im.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA") if has_alpha else im.convert("RGB")

    if len(raw) < SMALL_ORIGINAL_BYTES:
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


def guess_mime(path):
    ext = path.suffix.lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "application/octet-stream")


def prepare(n):
    db = load_db()
    pend = [m for m in db if m["status"] == "pending"]
    pend.sort(key=lambda m: m["original_filename"])
    batch = pend[:n]
    if not batch:
        print("Nenhum item pendente.")
        return
    WORK.mkdir(exist_ok=True)
    queue = []
    for m in batch:
        p = Path(m["source_path"])
        raw = p.read_bytes()
        opt, ext, note = optimize_image_bytes(raw, guess_mime(p))
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
            "id": m["id"], "original_filename": m["original_filename"],
            "local_file": str(local),
            "old_size_kb": m["old_size"] // 1024, "optimized_size_kb": len(opt) // 1024,
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
        print(f"  {q['local_file']}  ({q['original_filename']}, {q['old_size_kb']}KB -> {q['optimized_size_kb']}KB)")


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
                data = {"_payload": json.dumps({"alt": m["new_alt"] or ""}, ensure_ascii=False)}
                resp = requests.post(f"{auth['api']}/api/media",
                                      headers={"Authorization": f"{auth['scheme']} {auth['token']}"},
                                      files=files, data=data, timeout=120)
            if resp.status_code in (200, 201):
                doc = resp.json().get("doc", resp.json())
                m["new_media_id"] = doc.get("id")
                m["status"] = "uploaded"
                ok += 1
                print(f"  [OK] {m['original_filename']} -> {m['new_filename']} (novo ID {doc.get('id')})")
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
    print(f"\nTamanho original total: {total_old // 1024} KB")
    if total_new:
        n_proc = sum(1 for m in db if m.get("optimized_size"))
        print(f"Tamanho otimizado ({n_proc} já processados): {total_new // 1024} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", metavar="DIR")
    ap.add_argument("--prepare", type=int, metavar="N")
    ap.add_argument("--apply-names", action="store_true")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.seed:
        seed(args.seed)
    elif args.prepare:
        prepare(args.prepare)
    elif args.apply_names:
        apply_names()
    elif args.upload:
        upload()
    elif args.report:
        report()
    else:
        ap.error("use --seed DIR | --prepare N | --apply-names | --upload | --report")


if __name__ == "__main__":
    main()
