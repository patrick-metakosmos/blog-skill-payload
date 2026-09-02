<!--
  PONTEIRO DA SKILL - copie este arquivo para ~/.claude/skills/blog-mk-payload/SKILL.md
  e troque a linha BASE pelo caminho onde voce clonou este repositorio.
  Este e o arquivo oficial: nao escreva o ponteiro a mao, porque ele carrega as
  correcoes de rota e as regras do usuario, que mudam com o tempo.
-->

---
name: blog-mk-payload
description: Gera, reescreve, humaniza, audita e publica artigos do blog metaKosmos no Payload CMS (Lexical), e gera/posta o post de LinkedIn da página da metaKosmos a partir do artigo. Use quando o pedido envolver artigo do blog mK, pauta editorial, backlog/calendário editorial da mK, publicar post no metakosmos.com.br, ou post de LinkedIn da mK. Também cobre os modos Pautar, Gerar, Reescrever, Humanizar, Auditar, Publicar e LinkedIn. Piso duro: 2000+ palavras de corpo, FAQ 10+, zero em dash, keyword exata abrindo o H1, citação obrigatória do State of Immersive & Agentic Commerce 2026.
---

# Blog mK (Payload)

Esta skill é um **ponteiro**. A implementação real, as referências editoriais e os scripts vivem em uma única pasta de origem, para não duplicar o estudo de 9,2 MB nem sair de sincronia com o que o time edita.

**BASE:** `<AJUSTE AQUI: o caminho onde VOCE clonou este repositorio>`

## Primeiro passo, sempre

Leia o arquivo completo `BASE\SKILL.md` e siga-o à risca. Ele contém o fluxo de 9 passos, as regras bloqueadoras, os guardrails, a detecção automática de modo e o Completion Summary. Nada nesta página substitui aquele arquivo.

Depois, carregue as referências obrigatórias em `BASE\references\`:

`estudo-indice.md` (sempre), `manual-redacao.md`, `geo-aeo.md`, `pilares-conteudo.md`, `utm-tracking.md`, `mkases.md`, `style-dna.md`, `blog-patterns.md`, `anti-ia-rules.md`, `output-payload.md`, `concorrentes.md`, `processo-pauta.md`, `sitemap-urls.md`, `media-payload.md`, `[mK] Brand Book.txt`. No Modo LinkedIn, carregar também `linkedin-post.md`.

**Nunca** carregue `FINAL - The State of Immersive & Agentic Commerce 2026 powered by mK.md` inteiro (9,2 MB, linhas de até 1 milhão de caracteres). Localize a seção pelo `estudo-indice.md` e leia só aquele trecho por número de linha.

## Fila editorial

A fila oficial é `BASE\Pautas e Palavras Cahve\BACKLOG-EDITORIAL.md` (303 artigos, um por termo). Ao terminar um artigo, marque a linha correspondente com o status, a data e o slug. O `CALENDARIO-EDITORIAL.md` serve como diagnóstico de cobertura, não como fila.

## Scripts (rodar a partir de BASE)

```bash
python scripts/audit_artigo.py <slug>          # passo 8.5: formato + anti-IA + contagens. BLOQUEADOR.
python scripts/payload_publish.py <slug> --dry-run
python scripts/payload_publish.py <slug>       # cria rascunho (default)
python scripts/status_backlog.py               # cruza o backlog com o que existe no Payload
python scripts/sync_payload_lists.py           # atualiza blog-links.md (artigos) e mkases.md
python scripts/sync_payload_media.py           # atualiza o catálogo de imagens
python scripts/linkedin_publish.py <slug> --check    # valida o post de LinkedIn
python scripts/linkedin_publish.py <slug>            # POSTA na página da metaKosmos (ao vivo)
```

Os três primeiros rodam automaticamente ao final de cada publicação (ver Modo Publicar
em `BASE\SKILL.md`); não precisam de agendamento externo.

No Windows, prefixe com `PYTHONIOENCODING=utf-8` para o output não quebrar nos acentos.

## Correções de rota verificadas em 18/08/2026

Aplicam-se por cima do que estiver escrito nas referências antigas, que ainda são da era WordPress:

- **Posts vivem em `/blog/<slug>`.** As URLs de raiz herdadas do WP (`/roi-provador-virtual/`) retornam **404**. `blog-links.md` já foi portado (gerado por `scripts/sync_payload_lists.py` contra `/api/posts`); `sitemap-urls.md` ainda não.
- **mKases vivem em `/mkases/<slug>`**. `mkases.md` já foi portado (gerado por `scripts/sync_payload_lists.py` contra `/api/mkases`, só docs `published`) — se um slug não aparecer lá, ainda não está publicado.
- **LPs que retornam 404:** `/mk-ai-agent`, `/mk-skin-ai`, `/mk-home`. LPs que respondem 200: `/mk3d`, `/mk-3d-shop`, `/mk-fashion`, `/mk-beauty`, `/mklabs`, `/mk-spaces`, `/mk-3d-ads`, `/estudo`.
- **Verifique todo link por HTTP antes de entregar.** A API do Payload exige autenticação (`/api/users/login` via `.env`) para listar posts, mkases e categorias.
- **Pilares 5 e 7 não têm mapa em `PILAR_TO_CATEGORY_SLUG`.** Preencha o campo `Categoria:` do metadados à mão (`Guias` → slug `guias` funciona para o P5).

## Regras do usuário que valem por cima da skill

- **Publicar automaticamente AO VIVO** ao terminar um artigo, sem perguntar: `payload_publish.py <slug> --status published` (mudou de rascunho para ao vivo em 02/09/2026). Publicar como rascunho só se o usuário pedir. Não há mais revisão humana antes do público, então nenhum bloqueador da auditoria do passo 8.5 pode ser relevado.
- **Sem valores monetários** de preço ou piso de investimento no corpo. Sustente o argumento por redução percentual e ROI. Se um número for indispensável, sinalize no metadados e ofereça reinserir.
- **O piso da skill é duro** e prevalece sobre pedido menor: 2000+ palavras de corpo, sempre.
- **LinkedIn é automático de ponta a ponta**, e sai **depois** de o artigo ir ao ar: publicar o artigo ao vivo, escrever `output/[slug]/linkedin.md`, e então `linkedin_publish.py <slug>` (sem `--skip-link-check`, porque o link já está no ar e o HTTP 200 vira conferência de que o artigo subiu). O post entra ao vivo e público na página na hora; não existe rascunho por API. A ordem importa: invertida, todo post nasce em 404.
- **Uma vez por slug.** O LinkedIn não deduplica. O primeiro disparo grava `output/[slug]/.linkedin-posted.json` e a trava recusa os próximos; `--force` só com pedido explícito de repost.
- **O post de LinkedIn é teaser, não resumo:** 900 a 1.400 **caracteres** (~150 a 230 palavras), teto de 1.800. Ele abre a lacuna e para, para dar vontade de ler o artigo. Se responder a própria pergunta, matou o clique.
- **URL em 404 é aviso, não bloqueio.** No fluxo normal isso não acontece, porque o artigo sobe antes. Vale para repost ou post avulso de artigo ainda não publicado: o script avisa e posta assim mesmo, e o link passa a funcionar quando o artigo subir.
