#!/usr/bin/env python3
"""
linkedin_publish.py - Modo LinkedIn da skill blog-mk-payload

Dois destinos, cada um com arquivo, regras, trava e cenario do Make proprios:

  pagina (padrao)  output/[slug]/linkedin.md      -> pagina da metaKosmos
                   regras: references/linkedin-post.md
                   Make: Webhook -> LinkedIn v2 "Create a Company Text Post" (CreateTextShare)

  ceo              output/[slug]/linkedin-ceo.md  -> perfil pessoal do Ian Borges (CEO)
                   regras: references/linkedin-ceo.md (voz: guia de tom do Ian)
                   Make: Webhook -> LinkedIn v2 "Create a User Text Post" (CreatePost),
                   cenario 4928134. Link no proprio texto (LINKEDIN_CEO_LINK=corpo).

Os destinos sao independentes de proposito: se a conexao do Ian no Make expirar, so o
post dele para. O da pagina usa outra conexao e continua saindo.

Por que webhook do Make e nao API da LinkedIn direto:
a LinkedIn exige o produto "Community Management API" (aprovacao manual, app proprio,
token de 60 dias) para postar em pagina de empresa. O Make ja e parceiro aprovado e a
conexao LinkedIn da metaKosmos ja existe na conta, entao o custo de manutencao e zero.

Uso:
    python scripts/linkedin_publish.py --list [--perfil ceo]   # slugs com o arquivo pronto
    python scripts/linkedin_publish.py <slug> --check          # so valida, nao envia
    python scripts/linkedin_publish.py <slug> --dry-run        # valida e mostra o payload
    python scripts/linkedin_publish.py <slug>                  # valida e POSTA na pagina
    python scripts/linkedin_publish.py <slug> --perfil ceo     # valida e POSTA no perfil do Ian
    python scripts/linkedin_publish.py <slug> --skip-link-check
    python scripts/linkedin_publish.py <slug> --force          # reposta (a trava recusa por padrao)

Codigos de saida:
    0  ok: postado, ou validacao passou em --check / --dry-run
    1  erro: validacao reprovou, trava de duplicidade, webhook falhou
    3  destino nao configurado (webhook vazio no .env). NAO e falha: o destino ainda nao
       existe e o fluxo segue. Hoje vale para o perfil do CEO ate o Ian autorizar a
       conexao dele no Make.

O post e automatico no passo 10 do fluxo. Como o LinkedIn nao deduplica, o primeiro
disparo bem-sucedido grava um marcador por destino (.linkedin-posted.json na pagina,
.linkedin-ceo-posted.json no perfil do Ian) e qualquer disparo seguinte para nesse
marcador ate alguem passar --force.

.env (em "blog mK Payload/.env"):
    LINKEDIN_WEBHOOK_URL=https://hook.us1.make.com/xxxxxxxx       # pagina
    LINKEDIN_CEO_WEBHOOK_URL=https://hook.us1.make.com/yyyyyyyy   # perfil do Ian
    # opcionais:
    # LINKEDIN_ORG_URN=urn:li:organization:123456   (se o cenario nao fixar a pagina)
    # LINKEDIN_LINK_PREFIX=Leia completo em:
    # LINKEDIN_MAX_CHARS=1800
    # LINKEDIN_MIN_CHARS=500
    # LINKEDIN_CEO_LINK=corpo             (corpo | nenhum | comentario*)
    #   * comentario: o Make nao consegue comentar em perfil pessoal (403
    #     partnerApiSocialActions); so serve se alguem comentar a mao como o Ian.
    # LINKEDIN_CEO_COMMENT_PREFIX=Artigo completo aqui:

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

import ceo_antirrepeticao as anti   # orcamento de frases/estruturas do post do CEO

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

# Um destino = um arquivo, um marcador e um webhook. Nunca compartilham nada.
PERFIS = {
    "pagina": {
        "arquivo": "linkedin.md",
        "marcador": ".linkedin-posted.json",
        "webhook_env": "LINKEDIN_WEBHOOK_URL",
        "nome": "pagina da metaKosmos",
    },
    "ceo": {
        "arquivo": "linkedin-ceo.md",
        "marcador": ".linkedin-ceo-posted.json",
        "webhook_env": "LINKEDIN_CEO_WEBHOOK_URL",
        "nome": "perfil do Ian Borges (CEO)",
    },
}
EXIT_NAO_CONFIGURADO = 3

# --- perfil do CEO: numeros do guia de tom do Ian, secao 6 ---
CEO_MIN_CHARS = 800
CEO_MAX_CHARS = 1800
CEO_IDEAL = (1200, 1500)
CEO_HOOK_WARN = 140
CEO_LINK_MODES = ("comentario", "corpo", "nenhum")
CEO_DEFAULT_COMMENT_PREFIX = "Artigo completo aqui:"
# Separa, no GA4, o clique do perfil do Ian do clique da pagina (utm_content=[slug]).
CEO_UTM_CONTENT_PREFIX = "ian-"

EM_DASH = "—"
EN_DASH = "–"

FORBIDDEN_OPENERS = [
    "em conclusao", "para concluir", "concluindo", "em resumo", "resumindo",
    "em suma", "por fim", "para finalizar", "em ultima analise", "em sintese",
    "imagine que", "imagine um mundo", "parece ficcao cientifica",
    "pode parecer futurista", "parece distante", "neste artigo",
    "em um mundo cada vez mais", "no cenario atual", "pense num", "pense em",
]

# No perfil do Ian so as frases de conclusao sao proibidas: "Imagina so..." e
# assinatura dele (guia, secao 4), entao as aberturas da pagina nao valem la.
CONCLUSION_OPENERS = [
    "em conclusao", "para concluir", "concluindo", "em resumo", "resumindo",
    "em suma", "por fim", "para finalizar", "em ultima analise", "em sintese",
]

# Guia do Ian, secao 6: nunca palavrao. Comparado sem acento e por palavra inteira.
PALAVROES = [
    "porra", "caralho", "merda", "foda", "foda-se", "fodase", "puta", "puto",
    "cacete", "bosta", "pqp", "vsf", "fdp",
]

# Guia do Ian, secao 6: linguagem datada que expira. Bloqueia o que sempre envelhece;
# so avisa no que pode ser figurado ("o varejo de ontem").
TEMPO_BLOQUEADO = [
    "essa semana", "esta semana", "semana passada", "semana que vem",
    "proxima semana", "mes passado", "este mes", "esse mes",
]
TEMPO_AVISO = ["ontem", "anteontem", "hoje cedo", "hoje de manha"]

AI_WORDS = [
    "adicionalmente", "panorama", "alavancar", "sinergia", "holistico",
    "multifacetado", "intrincado", "disruptivo", "revolucionario", "transformador",
]

MONEY_RE = re.compile(r"R\$\s?\d|US\$\s?\d")
URL_RE = re.compile(r"https?://[^\s<>\"']+")
NUMBER_RE = re.compile(r"\d+([.,]\d+)?\s?%|\b\d{2,}\b")
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


def find_article_dir(slug, arquivo="linkedin.md"):
    """output/[slug] e tambem output/<Arquivo>/[slug] (mesma logica do payload_publish)."""
    direct = OUTPUT_DIR / slug
    if (direct / arquivo).exists():
        return direct
    for sub in ("Postado", "Arquivado", "Drafts"):
        cand = OUTPUT_DIR / sub / slug
        if (cand / arquivo).exists():
            return cand
    return None


def list_slugs(arquivo="linkedin.md"):
    found = []
    if not OUTPUT_DIR.exists():
        return found
    roots = [OUTPUT_DIR] + [OUTPUT_DIR / s for s in ("Postado", "Arquivado", "Drafts")]
    for root in roots:
        if not root.exists():
            continue
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / arquivo).exists():
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
# dois disparos = dois posts. O marcador abaixo e a unica coisa entre um re-run
# distraido e um post repetido em producao. Um marcador por destino.
MARKER_NAME = PERFIS["pagina"]["marcador"]


def read_marker(art_dir, nome=MARKER_NAME):
    path = art_dir / nome
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"posted_at": "desconhecido"}


def write_marker(art_dir, info, response, nome=MARKER_NAME, perfil="pagina"):
    path = art_dir / nome
    data = {
        "perfil": perfil,
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
    """Pagina da metaKosmos. Retorna (errors, warnings, info). errors sao bloqueadores."""
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
    if not NUMBER_RE.search(body_sem_url):
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


def _check_ceo_link(url, errors, warnings, info, skip_link_check):
    """UTMs do link do Ian: taxonomia padrao + utm_content com prefixo ian-."""
    info["url"] = url
    for key, expected in (("utm_source", "linkedin-organico"), ("utm_medium", "organic-social")):
        if f"{key}={expected}" not in url:
            errors.append(f"Link sem {key}={expected}.")
    if "utm_campaign=" not in url:
        errors.append("Link sem utm_campaign.")
    m = re.search(r"utm_content=([^&\s]+)", url)
    if not m:
        errors.append("Link sem utm_content.")
    elif not m.group(1).startswith(CEO_UTM_CONTENT_PREFIX):
        errors.append(
            f"utm_content={m.group(1)} tem que comecar com '{CEO_UTM_CONTENT_PREFIX}'. "
            "Sem o prefixo, o clique do perfil do Ian se mistura com o da pagina no GA4."
        )
    if not skip_link_check:
        status, err = check_url_live(url)
        info["url_status"] = status
        if err:
            warnings.append(f"Nao consegui verificar o link ({err}).")
        elif status != 200:
            warnings.append(f"Link respondeu {status}. O artigo ainda nao esta no ar.")


def validate_ceo(body, header, env, skip_link_check=False, slug=""):
    """Perfil pessoal do Ian Borges. Regras do guia de tom dele (secoes 6, 7 e 13),
    mais o orcamento anti-repeticao de ceo_antirrepeticao.py."""
    errors, warnings, info = [], [], {}
    lines = body.split("\n")
    n = len(body)
    info["chars"] = n
    info["lines"] = len(lines)

    # Padrao "corpo": comentar em perfil pessoal pela API exige acesso de parceiro do
    # LinkedIn que o Make nao tem (403 partnerApiSocialActions.CREATE, teste de 18/09/2026).
    # O padrao mora no codigo, nao no .env, para as duas maquinas se comportarem igual.
    modo = env.get("LINKEDIN_CEO_LINK", "corpo").strip().lower()
    if modo not in CEO_LINK_MODES:
        errors.append(f'LINKEDIN_CEO_LINK="{modo}" invalido. Use: {", ".join(CEO_LINK_MODES)}.')
        modo = "comentario"
    info["link_mode"] = modo
    info["comment"] = ""

    # --- tamanho (guia: 800 a 1.800, ideal 1.200 a 1.500) ---
    if n < CEO_MIN_CHARS or n > CEO_MAX_CHARS:
        errors.append(
            f"Post com {n} caracteres. O guia do Ian pede entre {CEO_MIN_CHARS} e {CEO_MAX_CHARS}."
        )
    elif not (CEO_IDEAL[0] <= n <= CEO_IDEAL[1]):
        warnings.append(
            f"Post com {n} caracteres. O ponto ideal de engajamento e {CEO_IDEAL[0]} a {CEO_IDEAL[1]}."
        )

    # --- gancho (pergunta e permitida no perfil do Ian) ---
    hook = lines[0].strip() if lines else ""
    info["hook"] = hook
    if not hook:
        errors.append("Primeira linha (gancho) vazia.")
    elif hook.startswith("#"):
        errors.append("Gancho comeca com hashtag.")
    elif len(hook) > CEO_HOOK_WARN:
        warnings.append(
            f"Gancho com {len(hook)} caracteres. No celular o 'ver mais' corta antes de ~{CEO_HOOK_WARN}."
        )

    # --- link, conforme o modo ---
    urls = URL_RE.findall(body)
    flat = strip_accents(body)
    link_hdr = header.get("link", "").strip()
    if modo == "comentario":
        if urls:
            errors.append(
                f"{len(urls)} URL(s) no corpo. No modo comentario o link vai so no primeiro comentario."
            )
        if not link_hdr:
            errors.append('Falta o campo "**Link:**" no cabecalho. E ele que vai no comentario.')
        else:
            _check_ceo_link(link_hdr, errors, warnings, info, skip_link_check)
            prefix = env.get("LINKEDIN_CEO_COMMENT_PREFIX", CEO_DEFAULT_COMMENT_PREFIX)
            info["comment"] = f"{prefix} {link_hdr}"
        if "coment" not in flat:
            warnings.append("O corpo nao avisa que o link esta nos comentarios. Ninguem vai procurar.")
    elif modo == "corpo":
        if len(urls) != 1:
            errors.append(f"{len(urls)} URLs no corpo. No modo corpo e exatamente 1.")
        # O erro do primeiro post real: prometeu "link nos comentarios" e nao havia comentario.
        if "nos comentarios" in flat:
            errors.append(
                "O post fala em link nos comentarios, mas no modo corpo nao ha comentario: "
                "o link esta no proprio texto."
            )
        if urls:
            _check_ceo_link(urls[0].rstrip(".,)"), errors, warnings, info, skip_link_check)
    else:  # nenhum
        if urls:
            errors.append(f"{len(urls)} URL(s) no corpo. No modo nenhum o post nao leva link.")

    # --- escrita (guia, secao 6) ---
    if EM_DASH in body:
        errors.append(f"{body.count(EM_DASH)} em dash no post. O guia do Ian proibe.")
    if EN_DASH in body:
        warnings.append(f"{body.count(EN_DASH)} en dash no post. Confira se e proposital.")
    for opener in CONCLUSION_OPENERS:
        for i, line in enumerate(lines):
            if strip_accents(line.strip()).startswith(opener):
                errors.append(f'Linha {i + 1} abre com frase de conclusao: "{opener}".')
    for p in PALAVROES:
        if re.search(rf"(?<![\w-]){re.escape(p)}(?![\w-])", flat):
            errors.append(f'Palavrao: "{p}". O guia proibe; troque por intensidade na frase.')
    if re.search(r"\bobrigada\b", flat):
        errors.append('"obrigada" na voz do Ian. O certo e "obrigado".')
    for t in TEMPO_BLOQUEADO:
        if re.search(rf"\b{t}\b", flat):
            errors.append(f'Tempo relativo "{t}". Envelhece: ancore num evento nomeado.')
    for t in TEMPO_AVISO:
        if re.search(rf"\b{t}\b", flat):
            warnings.append(f'"{t}" pode envelhecer. Confira se nao da para ancorar num evento.')
    for w in AI_WORDS:
        if re.search(rf"\b{w}", flat):
            warnings.append(f'Vocabulario de IA: "{w}".')

    # --- formato ---
    if "**" in body:
        errors.append("Markdown de negrito (**) no post. O LinkedIn nao renderiza.")
    for i, line in enumerate(lines):
        if line.strip().startswith(("- ", "* ")):
            warnings.append(f"Linha {i + 1} usa bullet markdown. Prefira paragrafo curto.")
    emojis = EMOJI_RE.findall(body)
    if emojis:
        errors.append(
            f"{len(emojis)} emoji grafico ({''.join(emojis[:5])}). "
            "O Ian so usa emoticon de caractere, tipo ;) e :)."
        )

    # --- dado (guia, secao 7: nunca afirmar sem dado) ---
    body_sem_url = body
    for u in urls:
        body_sem_url = body_sem_url.replace(u, "")
    if not NUMBER_RE.search(body_sem_url):
        errors.append("Nenhum numero no corpo. O Ian nunca afirma sem dado, case ou cenario concreto.")
    if MONEY_RE.search(body):
        warnings.append("Valor em R$ no post. Tamanho de mercado pode; preco e investimento nunca.")

    # --- opiniao, nao relatorio (o que reprovou a primeira amostra: 7 numeros e quase
    # nenhum "eu"). Avisos, porque voz nao se mede por regex; mas os dois pegam o padrao.
    pcts = re.findall(r"\d+(?:[.,]\d+)?\s?%", body_sem_url)
    if len(pcts) > 3:
        warnings.append(
            f"{len(pcts)} percentuais no corpo. Virou relatorio: o dado serve a opiniao, 1 ou 2 bastam."
        )
    if not re.search(r"\b(eu|me|meu|minha|meus|minhas|comigo|acho|acredito|aposto|confesso)\b", flat):
        warnings.append(
            "Nenhuma marca de primeira pessoa do singular. Opiniao do Ian vai em 'eu'; "
            "realizacao em 'a gente'."
        )

    # --- hashtags: 0 a 5, so na ultima linha ---
    todas = re.findall(r"(?<![\w&])#\w+", body)
    ultima = re.findall(r"(?<![\w&])#\w+", lines[-1]) if lines else []
    info["hashtags"] = ultima
    if len(todas) != len(ultima):
        errors.append("Hashtag fora da ultima linha. O guia pede todas no final.")
    if len(ultima) > 5:
        errors.append(f"{len(ultima)} hashtags. O maximo do guia e 5.")
    for t in ultima:
        if strip_accents(t) != t.lower():
            errors.append(f"Hashtag com acento: {t}.")

    # --- fechamento: CTA, provocacao ou pergunta (so aviso, CTA e dificil de detectar) ---
    texto = [l for l in lines if l.strip() and not re.fullmatch(r"(\s*#\w+)+\s*", l)]
    if texto and "?" not in texto[-1]:
        warnings.append("A ultima linha de texto nao e pergunta. Confira se fecha com CTA ou provocacao.")

    # --- anti-repeticao: frase-assinatura, abertura, fechamento, conviccao, ancora,
    # estrutura. Os 4 primeiros posts provaram que so voz e regra de formato nao
    # impedem o molde: sem orcamento, todo dia sai o mesmo post com outro assunto.
    err_rep, warn_rep, entrada = anti.checar(body, header, slug)
    errors.extend(err_rep)
    warnings.extend(warn_rep)
    info["anti"] = entrada

    return errors, warnings, info


def post_to_make(webhook, perfil, slug, body, info, env, timeout=60):
    payload = {
        "slug": slug,
        "content": body,
        "url": info.get("url", ""),
        "hook": info.get("hook", ""),
        "chars": info.get("chars", 0),
        "visibility": "PUBLIC",
    }
    if perfil == "pagina":
        org = env.get("LINKEDIN_ORG_URN", "").strip()
        if org:
            payload["organization"] = org
    else:
        payload["link_mode"] = info.get("link_mode", "")
        payload["comment"] = info.get("comment", "")

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace").strip()


def run(slug, perfil="pagina", check_only=False, dry_run=False, skip_link_check=False, force=False):
    cfg = PERFIS[perfil]
    art_dir = find_article_dir(slug, cfg["arquivo"])
    if not art_dir:
        log(f"Nao achei output/{slug}/{cfg['arquivo']}", "err")
        avail = list_slugs(cfg["arquivo"])
        if avail:
            log("Disponiveis: " + ", ".join(avail))
        return 1

    # Trava antes de qualquer coisa: se ja postou, so segue com --force.
    marker = read_marker(art_dir, cfg["marcador"])
    if marker and not (check_only or dry_run or force):
        log(f"Este slug JA foi postado no {cfg['nome']} em {marker.get('posted_at')}.", "err")
        log(f"Marcador: {art_dir / cfg['marcador']}", "info")
        log("O LinkedIn nao deduplica: postar de novo cria um segundo post.", "info")
        log("Se for mesmo para repostar, rode com --force.", "info")
        return 1

    env = load_env()
    header, body = parse_linkedin_md(art_dir / cfg["arquivo"])
    if not body.strip():
        log(f"{cfg['arquivo']} sem corpo (nada depois do ---).", "err")
        return 1

    if perfil == "ceo":
        errors, warnings, info = validate_ceo(body, header, env, skip_link_check=skip_link_check, slug=slug)
    else:
        errors, warnings, info = validate(body, env, skip_link_check=skip_link_check)

    print()
    print("=" * 60)
    print(f"LinkedIn - {slug} - {cfg['nome']}")
    print("=" * 60)
    palavras = len(body.split())
    if perfil == "ceo":
        print(f"Caracteres : {info.get('chars')}  (guia: {CEO_MIN_CHARS}-{CEO_MAX_CHARS}, "
              f"ideal {CEO_IDEAL[0]}-{CEO_IDEAL[1]})")
        print(f"Palavras   : {palavras}")
        print(f"Gancho     : {info.get('hook', '')[:80]}")
        print(f"Link       : modo {info.get('link_mode')} -> {info.get('url', '(nenhum)')}")
        if info.get("comment"):
            print(f"Comentario : {info['comment'][:80]}...")
    else:
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
        log(f"{len(errors)} bloqueador(es). Corrija o {cfg['arquivo']} antes de postar.", "err")
        return 1

    log("Validacao passou.", "ok")

    if check_only:
        return 0

    if dry_run:
        print()
        print("--- corpo que seria enviado ---")
        print(body)
        print("--- fim ---")
        if info.get("comment"):
            print()
            print("--- primeiro comentario ---")
            print(info["comment"])
            print("--- fim ---")
        print()
        log("dry-run: nada foi enviado ao Make.", "ok")
        return 0

    webhook = env.get(cfg["webhook_env"], "").strip()
    if not webhook:
        if perfil == "ceo":
            log(f"{cfg['nome']} ainda nao configurado: {cfg['webhook_env']} vazio no .env.", "warn")
            log("Nada foi postado. Isso NAO e falha: o post do Ian passa a sair quando o", "info")
            log("cenario dele existir no Make (depende de o Ian autorizar a conexao).", "info")
            return EXIT_NAO_CONFIGURADO
        raise SystemExit(
            f"[X] {cfg['webhook_env']} nao esta no .env. "
            "Crie o cenario no Make (Webhook -> LinkedIn Create a Company Text Post) "
            "e cole a URL do webhook."
        )

    if force and marker:
        log(f"--force: repostando um slug ja postado em {marker.get('posted_at')}.", "warn")

    status, resp = post_to_make(webhook, perfil, slug, body, info, env)
    if 200 <= status < 300:
        saved = write_marker(art_dir, info, resp, cfg["marcador"], perfil)
        if perfil == "ceo" and info.get("anti"):
            n = anti.registrar(info["anti"], body)
            log(f"Historico anti-repeticao atualizado ({n} posts).", "ok")
        log(f"Enviado ao Make (HTTP {status}). Resposta: {resp[:200]}", "ok")
        log(f"Marcador gravado ({saved['posted_at']}). Novo disparo so com --force.", "ok")
        log(f"Confira a execucao no Make e o post no {cfg['nome']}.", "info")
        return 0
    log(f"Webhook respondeu HTTP {status}: {resp[:300]}", "err")
    return 1


def main():
    ap = argparse.ArgumentParser(
        description="Posta o post de LinkedIn de um artigo (pagina da metaKosmos ou perfil do CEO) via Make."
    )
    ap.add_argument("slug", nargs="?", help="slug do artigo em output/")
    ap.add_argument("--perfil", choices=sorted(PERFIS), default="pagina",
                    help="destino: pagina (padrao) ou ceo (perfil pessoal do Ian Borges)")
    ap.add_argument("--list", action="store_true", help="lista slugs com o arquivo do destino pronto")
    ap.add_argument("--check", action="store_true", help="so valida, nao envia")
    ap.add_argument("--dry-run", action="store_true", help="valida e mostra o corpo, nao envia")
    ap.add_argument("--skip-link-check", action="store_true", help="nao bate HTTP na URL do artigo")
    ap.add_argument("--force", action="store_true", help="reposta um slug que ja foi postado")
    ap.add_argument("--historico", action="store_true",
                    help="perfil ceo: mostra o que esta queimado hoje (frases, conviccoes, aberturas)")
    args = ap.parse_args()

    if args.historico:
        print(anti.relatorio())
        return 0

    if args.list:
        slugs = list_slugs(PERFIS[args.perfil]["arquivo"])
        if not slugs:
            log(f"Nenhum {PERFIS[args.perfil]['arquivo']} em output/.", "warn")
            return 0
        for s in slugs:
            print(s)
        return 0

    if not args.slug:
        ap.print_help()
        return 1

    return run(
        args.slug,
        perfil=args.perfil,
        check_only=args.check,
        dry_run=args.dry_run,
        skip_link_check=args.skip_link_check,
        force=args.force,
    )


if __name__ == "__main__":
    sys.exit(main())
