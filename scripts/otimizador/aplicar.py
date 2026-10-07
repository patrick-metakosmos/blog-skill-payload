# -*- coding: utf-8 -*-
"""Aplica a otimização de um artigo no Payload (etapas 1.1.2.5 e 1.1.2.6).

Mais estreito que o `payload_publish --update`: só altera título, excerpt,
conteúdo e SEO (metaTitle/metaDescription) do locale pt-BR. Categoria, tags,
imagem de capa, publishedAt, slug e os locales en/es ficam como estão. São os
mesmos campos que o restore_post.py devolve, então reverter é um comando.

Antes do PATCH salva backup do post (formato do backup_all_posts, restaurável
com restore_post.py). Depois confere que o post continua publicado e que a
página responde 200.

Uso:
    python scripts/otimizador/aplicar.py <slug> --comparar   # prova de ida e volta (original.html == no ar)
    python scripts/otimizador/aplicar.py <slug> --dry-run    # mostra o diff do que mudaria
    python scripts/otimizador/aplicar.py <slug>              # aplica AO VIVO
Lê otimizador/trabalho/<slug>/artigo.html e seo.json.
"""
import argparse
import difflib
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import (  # noqa: E402
    SKILL_DIR, Converter, extract_excerpt, extract_h1_title, http, load_env, payload_login, resolve_images)

TRABALHO = SKILL_DIR / "otimizador" / "trabalho"
BACKUPS = SKILL_DIR / "backups"


def converter(html):
    conv = Converter()
    content = conv.convert(html)
    kids = content["root"]["children"]
    if kids and kids[0].get("type") == "paragraph":
        kids.pop(0)  # 1º parágrafo é o excerpt (mesma regra do payload_publish)
    return content, conv, extract_h1_title(html), extract_excerpt(html)


def normalizar(no):
    """Reduz um nó ao que aparece na página: tipo, texto, formato, tag, link,
    mídia. Junta textos vizinhos de mesmo formato (o Lexical às vezes parte)."""
    tipo = no.get("type")
    if tipo == "text":
        return {"t": "text", "x": no.get("text", ""), "f": no.get("format", 0) or 0}
    base = {"t": tipo}
    if tipo == "heading":
        base["tag"] = no.get("tag")
    if tipo == "list":
        base["ol"] = no.get("listType") == "number"
    if tipo == "link":
        base["url"] = (no.get("fields") or {}).get("url")
    if tipo == "upload":
        v = no.get("value")
        base["id"] = str(v.get("id") if isinstance(v, dict) else v)
    filhos = []
    for f in no.get("children", []):
        n = normalizar(f)
        if n["t"] == "text" and filhos and filhos[-1]["t"] == "text" and filhos[-1]["f"] == n["f"]:
            filhos[-1]["x"] += n["x"]
        else:
            filhos.append(n)
    if filhos:
        base["c"] = filhos
    return base


def linhas_legiveis(content):
    out = []

    def texto(n):
        if n["t"] == "text":
            return n["x"]
        inner = "".join(texto(c) for c in n.get("c", []))
        return f"[{inner}]({n['url']})" if n["t"] == "link" else inner

    for n in content:
        rot = n.get("tag") or n["t"]
        if n["t"] == "upload":
            out.append(f"[img {n['id']}]")
        elif n["t"] == "list":
            out += [f"- {texto(li)}" for li in n.get("c", [])]
        else:
            out.append(f"{rot}: {texto(n)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--comparar", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pasta = TRABALHO / args.slug
    seo_local = json.loads((pasta / "seo.json").read_text(encoding="utf-8"))
    pid = seo_local["id"]
    fonte = pasta / ("original.html" if args.comparar else "artigo.html")
    content, conv, titulo, excerpt = converter(fonte.read_text(encoding="utf-8"))

    auth = payload_login(load_env())
    code, vivo = http("GET", f"{auth['api']}/api/posts/{pid}?locale=pt-BR&depth=0",
                      token=auth["token"], scheme=auth["scheme"])
    if code != 200:
        raise SystemExit(f"[X] GET post {pid}: HTTP {code}")
    _, faltando = resolve_images(auth, content, conv)
    if faltando:
        raise SystemExit(f"[X] imagens fora da Media do Payload: {faltando}")

    novo = [normalizar(n) for n in content["root"]["children"]]
    atual = [normalizar(n) for n in vivo["content"]["root"]["children"]]

    if args.comparar:
        problemas = []
        if titulo != vivo["title"]:
            problemas.append(f"título: {titulo!r} != {vivo['title']!r}")
        if excerpt != (vivo.get("excerpt") or ""):
            problemas.append("excerpt diferente")
        if novo != atual:
            problemas.append("conteúdo diferente:\n" + "\n".join(difflib.unified_diff(
                linhas_legiveis(atual), linhas_legiveis(novo), "no ar", "ida e volta", lineterm="", n=1)))
        if problemas:
            print("[X] ida e volta NÃO reproduz o post:\n" + "\n".join(problemas))
            sys.exit(1)
        print(f"[OK] ida e volta idêntica: {len(atual)} blocos, título, excerpt e mídias batem")
        return

    seo = dict(vivo.get("seo") or {})
    seo.update({"metaTitle": seo_local["metaTitle"], "metaDescription": seo_local["metaDescription"]})
    corpo = {"title": titulo, "excerpt": excerpt, "content": content, "seo": seo}

    mudancas = []
    if titulo != vivo["title"]:
        mudancas.append(f"título: {vivo['title']!r} -> {titulo!r}")
    if excerpt != (vivo.get("excerpt") or ""):
        mudancas.append(f"excerpt: {vivo.get('excerpt')!r} -> {excerpt!r}")
    for campo in ("metaTitle", "metaDescription"):
        antes = (vivo.get("seo") or {}).get(campo) or ""
        if seo[campo] != antes:
            mudancas.append(f"seo.{campo}: {antes!r} -> {seo[campo]!r}")
    diff = list(difflib.unified_diff(linhas_legiveis(atual), linhas_legiveis(novo),
                                     "no ar", "otimizado", lineterm="", n=0))
    print("\n".join(mudancas) or "(título/excerpt/SEO sem mudança)")
    print(f"conteúdo: {len(atual)} -> {len(novo)} blocos, {sum(1 for l in diff if l[:1] in '+-') - 2} linhas alteradas")
    if args.dry_run:
        print("\n".join(diff[:400]))
        return

    # backup do post, restaurável com: python scripts/restore_post.py <pasta> <id>
    nome = f"otimizador_{datetime.now():%Y%m%d_%H%M}_post{pid}"
    bdir = BACKUPS / nome
    bdir.mkdir(parents=True)
    (bdir / f"post_{pid}_pt-BR.json").write_text(json.dumps(vivo, ensure_ascii=False, indent=1), encoding="utf-8")
    (bdir / "manifest.json").write_text(json.dumps({"posts": [{"id": pid, "slug": vivo["slug"],
                                                    "locales": {"pt-BR": f"post_{pid}_pt-BR.json"}}]},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")

    code, resp = http("PATCH", f"{auth['api']}/api/posts/{pid}?locale=pt-BR", body=corpo,
                      token=auth["token"], scheme=auth["scheme"])
    if code not in (200, 201):
        raise SystemExit(f"[X] PATCH falhou (HTTP {code}): {json.dumps(resp, ensure_ascii=False)[:500]}\n"
                         f"Nada foi alterado; backup em backups/{nome}")
    code, depois = http("GET", f"{auth['api']}/api/posts/{pid}?locale=pt-BR&depth=0",
                        token=auth["token"], scheme=auth["scheme"])
    publicado = depois.get("_status") == "published"
    try:
        status_pagina = urllib.request.urlopen(f"{auth['api']}/blog/{vivo['slug']}", timeout=30).status
    except Exception as e:  # noqa: BLE001
        status_pagina = str(e)
    print(f"[OK] post {pid} atualizado | _status={depois.get('_status')} | página {status_pagina}")
    print(f"Backup: backups/{nome}  (reverter: python scripts/restore_post.py {nome} {pid})")
    if not publicado or status_pagina != 200:
        print("[!] CONFERIR: o post não está publicado ou a página não respondeu 200")
        sys.exit(2)
    (pasta / "aplicado.json").write_text(json.dumps({"backup": nome, "quando": datetime.now().isoformat()},
                                                    ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
