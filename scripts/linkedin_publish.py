#!/usr/bin/env python3
"""
linkedin_publish.py - Modo LinkedIn da skill blog-mk-payload

Le output/[slug]/linkedin.md, valida contra as regras de references/linkedin-post.md
e dispara o post na pagina da metaKosmos atraves de um webhook do Make.

Por que webhook do Make e nao API da LinkedIn direto:
a LinkedIn exige o produto "Community Management API" (aprovacao manual, app proprio,
token de 60 dias) para postar em pagina de empresa. O Make ja e parceiro aprovado e a
conexao LinkedIn da metaKosmos ja existe na conta, entao o custo de manutencao e zero.
O cenario do Make e: Webhook -> LinkedIn v2 "Create a Company Text Post" (CreateTextShare),
visibility=PUBLIC, feedDistribution=MAIN_FEED.

Uso:
    python scripts/linkedin_publish.py --list                 # slugs com linkedin.md pronto
    python scripts/linkedin_publish.py <slug> --check         # so valida, nao envia
    python scripts/linkedin_publish.py <slug> --dry-run       # valida e mostra o payload
    python scripts/linkedin_publish.py <slug>                 # valida e POSTA no LinkedIn
    python scripts/linkedin_publish.py <slug> --skip-link-check
    python scripts/linkedin_publish.py <slug> --force         # reposta (a trava recusa por padrao)

O post e automatico no passo 10 do fluxo. Como o LinkedIn nao deduplica, o primeiro
disparo bem-sucedido grava output/[slug]/.linkedin-posted.json e qualquer disparo
seguinte para nesse marcador ate alguem passar --force.

.env (em "blog mK Payload/.env"):
    LINKEDIN_WEBHOOK_URL=https://hook.us1.make.com/xxxxxxxx
    # opcionais:
    # LINKEDIN_ORG_URN=urn:li:organization:123456   (se o cenario nao fixar a pagina)
    # LINKEDIN_LINK_PREFIX=Leia completo em:
    # LINKEDIN_MAX_CHARS=1800
    # LINKEDIN_MIN_CHARS=500

No Windows, rodar com PYTHONIOENCODING=utf-8 para os acentos nao quebrarem.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# === Config ===
SKILL_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = SKILL_DIR / "output"
ENV_FILE = SKILL_DIR / ".env"
USER_AGENT = "blog-mk-skill-payload/0.1"

DEFAULT_LINK_PREFIX = "Leia completo em:"
# CARACTERES, nao palavras. 900 a 1400 caracteres = ~150 a 230 palavras.
# Teto editorial da skill, abaixo dos 3000 que o LinkedIn aceita: o post e teaser,
# quem convence e o artigo.
DEFAULT_MAX_CHARS = 1800
DEFAULT_MIN_CHARS = 500

REQUIRED_UTMS = {
    "utm_source": "linkedin-organico",
    "utm_medium": "organic-social",
    "utm_campaign": None,   # so exige presenca
    "utm_content": None,
}

EM_DASH = "—"
EN_DASH = "–"

FORBIDDEN_OPENERS = [
    "em conclusao", "para concluir", "concluindo", "em resumo", "resumindo",
    "em suma", "por fim", "para finalizar", "em ultima analise", "em sintese",
    "imagine que", "imagine um mundo", "parece ficcao cientifica",
    "pode parecer futurista", "parece distante", "neste artigo",
    "em um mundo cada vez mais", "no cenario atual", "pense num", "pense em",
]

AI_WORDS = [
    "adicionalmente", "panorama", "alavancar", "sinergia", "holistico",
    "multifacetado", "intrincado", "disruptivo", "revolucionario", "transformador",
]

MONEY_RE = re.compile(r"R\$\s?\d|US\$\s?\d")
URL_RE = re.compile(r"https?://[^\s<>\"']+")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U0001F000-\U0001F2FF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF"
    "]"
)

ACCENT_MAP = {
    "á": "a", "à": "a", "ã": "a", "â": "a", "ä": "a",
    "é": "e", "ê": "e", "è": "e", "ë": "e",
    "í": "i", "î": "i", "ì": "i",
    "ó": "o", "ô": "o", "õ": "o", "ò": "o", "ö": "o",
    "ú": "u", "û": "u", "ù": "u", "ü": "u",
    "ç": "c", "ñ": "n",
}


def log(msg, level="info"):
    prefix = {"info": "[i]", "ok": "[OK]", "warn": "[!]", "err": "[X]"}.get(level, "[i]")
    print(f"{prefix} {msg}")


def strip_accents(s):
    return "".join(ACCENT_MAP.get(ch, ch) for ch in s.lower())


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def find_article_dir(slug):
    """output/[slug] e tambem output/<Arquivo>/[slug] (mesma logica do payload_publish)."""
    direct = OUTPUT_DIR / slug
    if (direct / "linkedin.md").exists():
        return direct
    for sub in ("Postado", "Arquivado", "Drafts"):
        cand = OUTPUT_DIR / sub / slug
        if (cand / "linkedin.md").exists():
            return cand
    return None


def list_slugs():
    found = []
    if not OUTPUT_DIR.exists():
        return found
    roots = [OUTPUT_DIR] + [OUTPUT_DIR / s for s in ("Postado", "Arquivado", "Drafts")]
    for root in roots:
        if not root.exists():
            continue
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / "linkedin.md").exists():
                rel = d.relative_to(OUTPUT_DIR)
                found.append(str(rel).replace("\\", "/"))
    return found


def parse_linkedin_md(path):
    """Cabecalho de controle acima do primeiro '---' isolado; corpo abaixo."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    sep = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            sep = i
            break
    if sep is None:
        header_lines, body_lines = [], lines
    else:
        header_lines, body_lines = lines[:sep], lines[sep + 1:]

    header = {}
    for line in header_lines:
        m = re.match(r"\*\*(.+?):\*\*\s*(.+)", line.strip())
        if m:
            header[m.group(1).strip().lower()] = m.group(2).strip()

    # tira linhas em branco nas pontas do corpo, preserva as do meio
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    return header, "\n".join(body_lines)


# =====================================================================
# Trava de duplicidade
# =====================================================================
# O post e automatico (passo 10 do fluxo) e o LinkedIn nao deduplica nada:
# dois disparos = dois posts na pagina. O marcador abaixo e a unica coisa
# entre um re-run distraido e um post repetido em producao.
MARKER_NAME = ".linkedin-posted.json"


def read_marker(art_dir):
    path = art_dir / MARKER_NAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"posted_at": "desconhecido"}


def write_marker(art_dir, info, response):
    path = art_dir / MARKER_NAME
    data = {
        "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url": info.get("url", ""),
        "chars": info.get("chars", 0),
        "hook": info.get("hook", ""),
        "webhook_response": response[:200],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def check_url_live(url, timeout=15):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return None, str(e)


def validate(body, env, skip_link_check=False):
    """Retorna (errors, warnings, info). errors sao bloqueadores."""
    errors, warnings, info = [], [], {}
    prefix = env.get("LINKEDIN_LINK_PREFIX", DEFAULT_LINK_PREFIX)
    max_chars = int(env.get("LINKEDIN_MAX_CHARS", DEFAULT_MAX_CHARS))
    min_chars = int(env.get("LINKEDIN_MIN_CHARS", DEFAULT_MIN_CHARS))

    lines = body.split("\n")
    n = len(body)
    info["chars"] = n
    info["lines"] = len(lines)

    # --- tamanho ---
    if n > max_chars:
        errors.append(
            f"Post com {n} caracteres, teto editorial e {max_chars}. "
            "E teaser, nao resumo: corte ate caber."
        )
    if n < min_chars:
        errors.append(f"Post com {n} caracteres, piso da skill e {min_chars}.")

    # --- gancho ---
    hook = lines[0].strip() if lines else ""
    info["hook"] = hook
    if not hook:
        errors.append("Primeira linha (gancho) vazia.")
    elif len(hook) > 100:
        errors.append(f"Gancho com {len(hook)} caracteres, teto e 100.")
    if hook.startswith("#"):
        errors.append("Gancho comeca com hashtag.")
    if hook.endswith("?"):
        warnings.append("Gancho e pergunta. A regra pede afirmacao ou dado.")

    # --- chamada do link logo depois do gancho ---
    link_idx = next((i for i, l in enumerate(lines) if l.strip().startswith(prefix)), None)
    if link_idx is None:
        errors.append(f'Falta a linha da chamada do link comecando com "{prefix}".')
    elif link_idx != 2:
        errors.append(
            f'A linha "{prefix}" esta na linha {link_idx + 1}; '
            "tem que ser a linha 3 (gancho, linha em branco, link)."
        )

    # --- URL e UTMs ---
    urls = URL_RE.findall(body)
    info["urls"] = urls
    if len(urls) == 0:
        errors.append("Nenhuma URL no post.")
    elif len(urls) > 1:
        errors.append(f"{len(urls)} URLs no post. A regra e exatamente 1.")

    if urls:
        url = urls[0].rstrip(".,)")
        info["url"] = url
        for key, expected in REQUIRED_UTMS.items():
            if f"{key}=" not in url:
                errors.append(f"URL sem {key}.")
            elif expected and f"{key}={expected}" not in url:
                errors.append(f"URL com {key} errado, tem que ser {key}={expected}.")
        if not skip_link_check:
            status, err = check_url_live(url)
            info["url_status"] = status
            if err:
                warnings.append(f"Nao consegui verificar a URL ({err}).")
            elif status != 200:
                # Aviso, nao bloqueador: decisao do usuario e poder postar antes do
                # artigo estar no ar, porque em algum momento ele vai estar.
                warnings.append(
                    f"URL respondeu {status}. O artigo ainda nao esta ao vivo no Payload, "
                    "entao quem clicar agora cai em 404. Postando mesmo assim."
                )

    # --- anti-IA ---
    if EM_DASH in body:
        errors.append(f"{body.count(EM_DASH)} em dash no post. Tolerancia zero.")
    if EN_DASH in body:
        warnings.append(f"{body.count(EN_DASH)} en dash no post. Confira se e proposital.")

    flat = strip_accents(body)
    for opener in FORBIDDEN_OPENERS:
        for i, line in enumerate(lines):
            if strip_accents(line.strip()).startswith(opener):
                errors.append(f'Linha {i + 1} abre com expressao proibida: "{opener}".')
    for w in AI_WORDS:
        if re.search(rf"\b{w}", flat):
            warnings.append(f'Vocabulario de IA: "{w}".')

    # --- markdown e emoji ---
    if "**" in body:
        errors.append("Markdown de negrito (**) no post. O LinkedIn nao renderiza.")
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("#") and not re.match(r"#\w", s):
            errors.append(f"Linha {i + 1} parece heading markdown.")
        if s.startswith(("- ", "* ")):
            warnings.append(f"Linha {i + 1} usa bullet markdown. Prefira bloco de texto.")
    emojis = EMOJI_RE.findall(body)
    if emojis:
        errors.append(
            f"{len(emojis)} emoji no post ({''.join(emojis[:5])}). Pagina de empresa nao usa."
        )

    # --- dinheiro ---
    if MONEY_RE.search(body):
        errors.append("Valor monetario no post. A regra da mK e sustentar por percentual e ROI.")

    # --- dado numerico (proxy do dado do estudo) ---
    body_sem_url = body
    for u in urls:
        body_sem_url = body_sem_url.replace(u, "")
    if not re.search(r"\d+([.,]\d+)?\s?%|\b\d{2,}\b", body_sem_url):
        errors.append("Nenhum numero no corpo. O post precisa de pelo menos 1 dado do estudo.")

    # --- hashtags ---
    tags = re.findall(r"#\w+", lines[-1]) if lines else []
    info["hashtags"] = tags
    if len(tags) < 3:
        errors.append(f"{len(tags)} hashtags na ultima linha. O minimo e 3.")
    elif len(tags) > 5:
        errors.append(f"{len(tags)} hashtags na ultima linha. O maximo e 5.")
    for t in tags:
        if strip_accents(t) != t.lower():
            errors.append(f"Hashtag com acento: {t}.")

    # --- anafora staccato ---
    run, prev_first = 0, None
    for line in lines:
        for sent in re.split(r"(?<=[.!?])\s+", line.strip()):
            words = sent.split()
            if not words:
                continue
            first = strip_accents(words[0])
            if len(words) <= 10 and first == prev_first:
                run += 1
                if run >= 2:
                    warnings.append(
                        f'Anafora staccato: 3+ frases curtas abrindo com "{words[0]}".'
                    )
                    run = 0
            else:
                run = 0
            prev_first = first

    return errors, warnings, info


def post_to_make(env, slug, body, info, timeout=60):
    webhook = env.get("LINKEDIN_WEBHOOK_URL", "").strip()
    if not webhook:
        raise SystemExit(
            "[X] LINKEDIN_WEBHOOK_URL nao esta no .env. "
            "Crie o cenario no Make (Webhook -> LinkedIn Create a Company Text Post) "
            "e cole a URL do webhook."
        )
    payload = {
        "slug": slug,
        "content": body,
        "url": info.get("url", ""),
        "hook": info.get("hook", ""),
        "chars": info.get("chars", 0),
        "visibility": "PUBLIC",
    }
    org = env.get("LINKEDIN_ORG_URN", "").strip()
    if org:
        payload["organization"] = org

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace").strip()


def run(slug, check_only=False, dry_run=False, skip_link_check=False, force=False):
    art_dir = find_article_dir(slug)
    if not art_dir:
        log(f"Nao achei output/{slug}/linkedin.md", "err")
        avail = list_slugs()
        if avail:
            log("Disponiveis: " + ", ".join(avail))
        return 1

    # Trava antes de qualquer coisa: se ja postou, so segue com --force.
    marker = read_marker(art_dir)
    if marker and not (check_only or dry_run or force):
        log(f"Este slug JA foi postado em {marker.get('posted_at')}.", "err")
        log(f"Marcador: {art_dir / MARKER_NAME}", "info")
        log("O LinkedIn nao deduplica: postar de novo cria um segundo post na pagina.", "info")
        log("Se for mesmo para repostar, rode com --force.", "info")
        return 1

    env = load_env()
    header, body = parse_linkedin_md(art_dir / "linkedin.md")
    if not body.strip():
        log("linkedin.md sem corpo (nada depois do ---).", "err")
        return 1

    errors, warnings, info = validate(body, env, skip_link_check=skip_link_check)

    print()
    print("=" * 60)
    print(f"LinkedIn - {slug}")
    print("=" * 60)
    palavras = len(body.split())
    print(f"Caracteres : {info.get('chars')}  (alvo 900-1400, teto 1800)")
    print(f"Palavras   : {palavras}  (alvo ~150-230)")
    print(f"Gancho     : {info.get('hook', '')[:80]}")
    print(f"URL        : {info.get('url', '(nenhuma)')}")
    if "url_status" in info:
        print(f"HTTP       : {info['url_status']}")
    print(f"Hashtags   : {' '.join(info.get('hashtags', [])) or '(nenhuma)'}")
    print("=" * 60)
    print()

    for w in warnings:
        log(w, "warn")
    for e in errors:
        log(e, "err")

    if errors:
        print()
        log(f"{len(errors)} bloqueador(es). Corrija o linkedin.md antes de postar.", "err")
        return 1

    log("Validacao passou.", "ok")

    if check_only:
        return 0

    if dry_run:
        print()
        print("--- corpo que seria enviado ---")
        print(body)
        print("--- fim ---")
        print()
        log("dry-run: nada foi enviado ao Make.", "ok")
        return 0

    if force and marker:
        log(f"--force: repostando um slug ja postado em {marker.get('posted_at')}.", "warn")

    status, resp = post_to_make(env, slug, body, info)
    if 200 <= status < 300:
        saved = write_marker(art_dir, info, resp)
        log(f"Enviado ao Make (HTTP {status}). Resposta: {resp[:200]}", "ok")
        log(f"Marcador gravado ({saved['posted_at']}). Novo disparo so com --force.", "ok")
        log("Confira a execucao no Make e o post na pagina da metaKosmos.", "info")
        return 0
    log(f"Webhook respondeu HTTP {status}: {resp[:300]}", "err")
    return 1


def main():
    ap = argparse.ArgumentParser(
        description="Posta o linkedin.md de um artigo na pagina da metaKosmos via Make."
    )
    ap.add_argument("slug", nargs="?", help="slug do artigo em output/")
    ap.add_argument("--list", action="store_true", help="lista slugs com linkedin.md pronto")
    ap.add_argument("--check", action="store_true", help="so valida, nao envia")
    ap.add_argument("--dry-run", action="store_true", help="valida e mostra o corpo, nao envia")
    ap.add_argument("--skip-link-check", action="store_true", help="nao bate HTTP na URL do artigo")
    ap.add_argument("--force", action="store_true", help="reposta um slug que ja foi postado")
    args = ap.parse_args()

    if args.list:
        slugs = list_slugs()
        if not slugs:
            log("Nenhum linkedin.md em output/.", "warn")
            return 0
        for s in slugs:
            print(s)
        return 0

    if not args.slug:
        ap.print_help()
        return 1

    return run(
        args.slug,
        check_only=args.check,
        dry_run=args.dry_run,
        skip_link_check=args.skip_link_check,
        force=args.force,
    )


if __name__ == "__main__":
    sys.exit(main())
