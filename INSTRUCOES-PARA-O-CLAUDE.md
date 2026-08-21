# Runbook de Setup — para o Claude executar

> **Para a pessoa:** abra o Claude nesta pasta e diga:
> *"Leia o arquivo INSTRUCOES-PARA-O-CLAUDE.md e execute o setup desta skill pra mim."*
> O Claude vai seguir os passos abaixo sozinho, pedindo sua aprovação nos comandos.

---

## Contexto (Claude, leia isto primeiro)

Esta é a skill **Blog mK (Payload)** — um gerador de artigos de blog que escreve em HTML semântico e publica no Payload CMS da metaKosmos como rascunho. Ela **não é um plugin instalado**: é esta pasta, e você a usa lendo o `SKILL.md` e os arquivos de `references/`.

Existe uma versão ANTIGA (WordPress) com nome parecido no catálogo de skills do app. **Ignore-a.** Use sempre o `SKILL.md` desta pasta.

Sua tarefa agora é deixar o ambiente pronto para a pessoa gerar e publicar artigos. Execute os passos na ordem.

---

## Passo 1 — Verificar o Python

Rode:
```
python --version
```
- Se responder Python 3.8 ou superior: siga em frente.
- Se não existir `python`, tente `py --version` ou `python3 --version`.
- Se nenhum funcionar: avise a pessoa que ela precisa instalar o Python 3 (https://www.python.org/downloads/ ou `winget install Python.Python.3.12` no Windows) e pare aqui.

**Não instale nenhum pacote pip.** Os scripts usam só a biblioteca padrão do Python.

---

## Passo 2 — Criar o arquivo `.env`

O `.env` guarda o login do painel Payload usado para publicar. Ele **não vem no pacote** (por segurança).

1. Verifique se já existe um `.env` na raiz da pasta. Se existir, pule para o Passo 3.
2. Se não existir, copie o modelo:
   - Leia o `.env.example`.
   - Crie um novo arquivo `.env` na raiz com o mesmo conteúdo.
3. Preencha os campos obrigatórios:
   ```
   PAYLOAD_API_URL=https://metakosmos.com.br
   PAYLOAD_EMAIL=<peça o e-mail do painel Payload da pessoa>
   PAYLOAD_PASSWORD=<ver abaixo>
   ```
4. **Sobre a senha (importante):** pergunte à pessoa como ela prefere:
   - **(a)** ela mesma abre o `.env` e digita a senha na linha `PAYLOAD_PASSWORD=` (mais seguro); ou
   - **(b)** ela cola a senha no chat e você escreve no `.env` local.
   
   O `.env` é um arquivo **local** na máquina dela e nunca deve ser compartilhado nem versionado.

---

## Passo 3 — Testar o login (sem publicar nada)

Use qualquer slug que exista em `output/` (ex.: `roi-provador-virtual`, que vem como exemplo):
```
python scripts/payload_publish.py roi-provador-virtual --probe
```
- Esperado: `Token obtido (user: ...)` e as coleções `posts / categories / tags / media` com HTTP 200.
- Se der erro de credencial: confira `PAYLOAD_EMAIL` / `PAYLOAD_PASSWORD` no `.env`.
- Se der erro de conexão: confira `PAYLOAD_API_URL`.

---

## Passo 4 — Atualizar o catálogo de imagens (recomendado)

O catálogo `references/media-payload.md` lista as imagens reais disponíveis no Payload. Para deixá-lo atual:
```
python scripts/sync_payload_media.py
```
Isso regenera o catálogo a partir de `/api/media`. Faça isso sempre que entrarem mídias novas no CMS.

---

## Passo 5 — Confirmar que a skill está pronta para uso

Avise a pessoa que está tudo pronto e explique como pedir cada modo:

| A pessoa quer... | Ela diz algo como... |
|------------------|----------------------|
| Um briefing/pauta | "Faz uma **pauta** para a keyword X, pilar Y, funil MOFU." |
| Um artigo do zero | "**Gera** um artigo sobre [tema/título]." |
| Reescrever um texto | Cola o texto + "reescreve na voz mK." |
| Limpar padrões de IA | Cola o texto + "**humaniza** isso." |
| Avaliar um texto | Cola o texto + "**audita** e dá o score." |
| Publicar | "**Publica** o artigo [slug]." |

Sempre que for gerar/reescrever, **leia antes** o `SKILL.md` e TODOS os arquivos de `references/`.

---

## Passo 6 — Como publicar (quando ela pedir)

Depois que o artigo estiver em `output/[slug]/` (com `artigo.html` + `metadados.md`):
```
python scripts/payload_publish.py <slug> --dry-run   # valida a conversão para Lexical, sem tocar na API
python scripts/payload_publish.py <slug> --probe     # confirma o login
python scripts/payload_publish.py <slug>             # cria o RASCUNHO no Payload (default)
```
- O padrão é **rascunho** — nada vai ao ar sem revisão humana no painel. Não use `--status published` sem a pessoa pedir e confirmar.
- Confirme com ela que os dados numéricos do artigo estão auditados antes de publicar.

---

## Regras que você (Claude) deve respeitar

- **Nunca** publique com `--status published` sem pedido + confirmação explícita da pessoa.
- **Nunca** compartilhe, versione ou imprima o conteúdo do `.env`.
- **Não** invente URLs nem dados: links só de `sitemap-urls.md`/`blog-links.md`, imagens só de `media-payload.md`, números só com fonte.
- Siga o piso da skill: mínimo 2.000 palavras no corpo, FAQ 10+, zero em dash, formato HTML semântico.
