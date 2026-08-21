# Handoff — Skill "Blog mK (Payload)"

Guia para outra pessoa usar esta skill no Claude (mesmo app), em outro computador e no login dela.

Esta skill **não é um plugin instalado** no Claude: é uma **pasta** que o Claude lê. Para usar, basta apontar o Claude para o `SKILL.md` desta pasta.

---

## 1. O que transferir

Copie a pasta **`blog mK Payload/`** inteira. O essencial:

| Item | Precisa? | Observação |
|------|----------|------------|
| `SKILL.md` | ✅ Sim | O cérebro da skill. O Claude lê e segue. |
| `references/` (arquivos `.md` + `.txt`) | ✅ Sim | Voz, GEO/AEO, pilares, mKases, UTMs, catálogo de imagens (`media-payload.md`), URLs verificadas (`sitemap-urls.md`), Brand Book. |
| `scripts/` | ✅ Sim | `payload_publish.py` (publica) e `sync_payload_media.py` (atualiza catálogo de imagens). |
| `.env` | ⚠️ Recriar | **NÃO copie o `.env` com as senhas.** Ver seção 3. |
| `output/` | Opcional | Artigos já feitos (servem de exemplo). Pode levar 1-2 como referência. |
| `backups/` | ❌ Não | Backups pesados de posts antigos. Dispensável. |
| `references/assets-db.json`, `media-library.md` | ❌ Não | Legado do WordPress. Não é usado no Payload. |

Forma mais simples: zipar a pasta, **apagar `.env` e `backups/`** do zip, e enviar.

---

## 2. Pré-requisitos no computador da pessoa

1. **Claude** (mesmo app desktop/Claude Code que você usa).
2. **Python 3.8+** instalado (`python --version` deve responder).
   - Os scripts usam **só a biblioteca padrão** do Python. **Não precisa `pip install` de nada.**

---

## 3. Configurar o `.env` (credenciais)

O `.env` guarda o login do painel Payload que o script usa para publicar. **Segurança:**

- **Não mande senha por e-mail/chat em texto puro.** Use um gerenciador de senhas ou canal seguro.
- **Ideal:** a pessoa cria o **próprio login** no painel Payload (os posts ficam registrados no usuário dela).

Passo a passo:
1. Copie `.env.example` para `.env` na raiz da pasta.
2. Preencha:
   ```
   PAYLOAD_API_URL=https://metakosmos.com.br
   PAYLOAD_EMAIL=<email dela no painel Payload>
   PAYLOAD_PASSWORD=<senha dela no painel Payload>
   ```
3. Teste o login (sem publicar nada):
   ```
   python scripts/payload_publish.py <qualquer-slug-de-output> --probe
   ```
   Deve responder `Token obtido` e listar as coleções.

---

## 4. Como usar a skill no Claude

Abra o Claude na pasta (ou com acesso a ela) e diga algo como:

> "Tenho uma skill de blog em `.../blog mK Payload`. Leia o `SKILL.md` e as referências antes de começar. Quero uma **pauta** para a keyword X, pilar Y." (ou "**gera** um artigo sobre...", "**audita** este texto", etc.)

O Claude vai:
1. Ler o `SKILL.md` + todos os `references/`.
2. Detectar o modo (Pautar / Gerar / Reescrever / Humanizar / Auditar / Publicar).
3. Gerar os 3 documentos em `output/[slug]/`: `pauta.md`, `artigo.html`, `metadados.md`.
4. Rodar as auditorias (anti-IA, GEO/AEO, formato Payload).

**Dica:** peça sempre para o Claude "seguir o `SKILL.md` desta pasta", já que existe também uma versão antiga (WordPress) com o mesmo nome no catálogo de skills do app. As duas são diferentes; esta (Payload) é a atual.

---

## 5. Publicar (opcional)

Depois que o artigo estiver em `output/[slug]/`:

```
python scripts/payload_publish.py <slug> --dry-run   # valida a conversão p/ Lexical, sem API
python scripts/payload_publish.py <slug> --probe     # testa login
python scripts/payload_publish.py <slug>             # cria RASCUNHO no Payload (default)
```

- O default é **rascunho** — nada vai ao ar sem revisão humana no painel.
- O script resolve categoria (por pilar), tags (cria as que faltam), imagens da Media e featuredImage.

---

## 6. Manter o catálogo de imagens atualizado

As imagens só podem sair de `references/media-payload.md`. Quando entrarem mídias novas no Payload:

```
python scripts/sync_payload_media.py
```

Isso regenera `media-payload.md` a partir de `/api/media` (precisa do `.env` configurado).

---

## Resumo rápido

1. Copiar a pasta (sem `.env` e sem `backups/`).
2. Ter Python 3 (sem instalar pacotes).
3. Criar `.env` a partir do `.env.example` com o login Payload da pessoa.
4. No Claude: "leia o `SKILL.md` desta pasta e siga".
5. Publicar com `python scripts/payload_publish.py <slug>` (nasce rascunho).
