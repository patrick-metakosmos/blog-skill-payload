---
name: blog-mk-payload
version: 1.0.0
description: |
  Gerador e reescritor de artigos de blog metaKosmos para o **Payload CMS** (Lexical), com voz autenticada, anti-IA integrado, GEO/AEO otimizado e self-audit.
  Clone da skill blog-mk (WordPress/Gutenberg), adaptado ao Payload: o corpo é escrito em HTML semântico simples e convertido para Lexical na publicação. A skill blog-mk original permanece intocada para o legado WP.
  5 modos: Pautar, Gerar, Reescrever, Humanizar, Auditar + Publicar + LinkedIn. Detecção automática por contexto.
  Fluxo em 10 passos: input → pesquisa → pauta → escrita em chunks 1000w → integração → auditoria → revisão editorial → HTML semântico final → entrega → publicação (artigo AO VIVO + post no LinkedIn).
  Output: 3 documentos — (1) Pauta .md, (2) Artigo .html (HTML semântico → Lexical), (3) Ficha de Metadados .md — mais (4) linkedin.md, gerado automático no passo 10.
  Regras: min 2000 palavras, parágrafos 35-40 palavras, FAQ 10+ perguntas, links verificados. SEM componentes visuais (Payload é plano).
  Keyword-alvo exata na abertura do H1. Todo artigo cita o State of Immersive & Agentic Commerce 2026 e tem CTA para /estudo.
tools-necessários:
  - Read (arquivos de referência)
  - Create File (4 arquivos de output)
  - WebFetch (Google Docs, se usuário fornecer URL)
  - WebSearch (pesquisa de dados/fontes externas quando necessário)
---

# Blog mK (Payload) — Gerador de Artigos

## Diferença vs skill blog-mk (WordPress)

Esta é a variante **Payload** da skill de blog. O CMS do metakosmos.com.br migrou de WordPress (Gutenberg) para **Payload CMS**, cujo campo `content` é uma árvore **Lexical (JSON)**. Consequências que mudam a geração:

- **Payload é plano.** O Lexical de vocês usa só primitivos (parágrafo, heading, lista, link, imagem, linha, negrito). **Não existem blocos customizados.** Todo o "chrome visual" do Gutenberg (cards de mKase, botões CTA, colunas 50/50, stat boxes, cores de fundo, spacers) **é achatado**. Portanto **não escreva esses componentes** — dão trabalho e somem.
- **O artigo é escrito em HTML semântico simples** (`artigo.html`) e o `payload_publish.py` converte para Lexical na publicação. Ver `references/output-payload.md`.
- **Publicar** usa `scripts/payload_publish.py` (não `wp_publish.py`). Auth por login/senha do Payload; sem Yoast; categoria por pilar; tags por slug.

Tudo que é **editorial** (voz, anti-IA, GEO/AEO, mKases, links, tamanho, FAQ) é **idêntico** à skill original e vive nos mesmos arquivos de referência.

**Cada execução produz 4 documentos dentro de uma pasta dedicada por artigo:**

```
output/
└── [slug-do-artigo]/
    ├── pauta.md
    ├── artigo.html      (HTML semântico → convertido para Lexical)
    ├── metadados.md
    └── linkedin.md      (4º documento, automático no passo 10)
```

| # | Documento | Caminho | Conteúdo |
|---|-----------|---------|----------|
| 1 | **Pauta Completa** | `output/[slug]/pauta.md` | Briefing editorial completo (Modo Pautar) |
| 2 | **Artigo Payload** | `output/[slug]/artigo.html` | **HTML semântico simples** (h1/h2/h3, p, strong, ul/li, a, img, hr). Mínimo 2000 palavras, parágrafos 35-40 palavras, FAQ 10+. SEM cards/colunas/botões/cores/`style=`. Convertido para Lexical na publicação. SEM sumário/ToC (Payload gera). |
| 3 | **Ficha de Metadados** | `output/[slug]/metadados.md` | SEO (Título SEO, Meta Description, Slug, Pilar, Categoria, Tags), checklist pré-publicação, self-audit, instruções para o editor |
| 4 | **Post de LinkedIn** | `output/[slug]/linkedin.md` | Teaser da página da metaKosmos: gancho, `Leia completo em:` + link com UTM, 3-4 blocos, hashtags. 900-1.400 caracteres. Gerado e **publicado ao vivo** no passo 10, depois do artigo subir |

---

## Arquivos de Referência

Carregar TODOS antes de iniciar qualquer modo:

```
references/estudo-indice.md       — ÍNDICE + 139 DADOS CITÁVEIS do State of Immersive & Agentic Commerce 2026  ← CARREGAR SEMPRE
references/manual-redacao.md      — Produtos, personas, diferenciais, tom, estrutura, metas
references/geo-aeo.md             — 8 regras GEO/AEO, hierarquia citável, checklist GEO
references/pilares-conteudo.md    — 7 pilares com funil, keywords e pillar pages
references/utm-tracking.md        — Taxonomia UTM oficial, padrões por pilar, links internos
references/mkases.md              — Cases com métricas (mínimo 2 por artigo)
references/blog-links.md          — URLs para linking interno (2-3 por artigo)
references/style-dna.md           — Trechos reais do blog (âncora de voz)
references/blog-patterns.md       — Padrões estruturais + estrutura GEO/AEO
references/anti-ia-rules.md       — 25 padrões proibidos + checklist unificado 30 itens
references/output-payload.md      — Formato do artigo (HTML semântico) + mapeamento p/ Lexical  ← ESPECÍFICO DESTA SKILL
references/linkedin-post.md       — Regras do post de LinkedIn (estrutura, tamanho, UTM, checklist)  ← MODO LINKEDIN
references/concorrentes.md        — Mapa competitivo (JAMAIS linkar concorrentes)
references/processo-pauta.md      — Template e fluxo de criação de pauta
references/sitemap-urls.md        — Todas as URLs verificadas do site (sitemaps)
references/media-payload.md       — CATÁLOGO REAL da Media do Payload (352 imagens) — fonte única de imagens  ← USAR ESTE
references/[mK] Brand Book.txt    — Cores/tipografia/tom (referência de VOZ; cores NÃO renderizam no Payload)

references/FINAL - The State of Immersive & Agentic Commerce 2026 powered by mK.md
                                  — ESTUDO COMPLETO. 9,2 MB, 44 blocos base64, linhas de até 1 milhão
                                    de caracteres. NUNCA carregar inteiro: localizar a seção pelo
                                    `estudo-indice.md` e ler SÓ aquele trecho (por número de linha).
```

**Nota sobre imagens:** a fonte de imagens é `references/media-payload.md` (gerado por `scripts/sync_payload_media.py` a partir de `/api/media`). Referencie imagens SÓ por nomes que existem nesse catálogo. `media-library.md`/`blog-links.md` ainda são do WordPress e não valem para imagens do Payload. Rodar `python scripts/sync_payload_media.py` quando quiser atualizar o catálogo.

---

## Regras Obrigatórias (editoriais — iguais à blog-mk)

### Título e keyword-alvo (BLOQUEADOR)

- **A keyword-alvo aparece EXATA e na ABERTURA do `<h1>`.** Formato canônico:
  `<Keyword exata>: <complemento diferenciador>`.
- **Proibido parafrasear a keyword no título.** Se a keyword é `tabela de medidas roupas online`,
  o H1 não pode virar "Tabela de medidas: por que ela falha". Tem que conter a string inteira.
- **Palavras de ligação intercaladas são aceitas** (de, do, da, no, na, em, com, para, e).
  `diagnóstico pele preditivo IA` → "Diagnóstico **de** pele preditivo **com** IA" continua válido.
  Sinônimo e reordenação **não** valem: trocar "tamanho" por "número" quebra a regra.
- **O complemento não pode ecoar a keyword.** "Como aumentar faturamento e-commerce: como aumentar
  o faturamento do e-commerce" está errado. O complemento entrega o ângulo, o dado ou a promessa.
- **A keyword também vai no primeiro parágrafo** (dentro das primeiras 150 palavras, regra GEO)
  e em pelo menos um H2 ou pergunta do FAQ.
- **Título SEO ≤60c no metadados:** quando o H1 passar de 60 caracteres, a versão curta do metadados
  corta o complemento e **nunca** o termo — ela também abre pela keyword.

### Estudo: fonte obrigatória em TODO artigo (BLOQUEADOR)

Todo artigo cita o **State of Immersive & Agentic Commerce 2026** e manda tráfego para ele.

- **Mínimo 1 dado do estudo citado no corpo**, com o número, o recorte e a fonte quando houver.
  Puxar de `references/estudo-indice.md` (139 trechos com estatística já extraídos) e **conferir
  no arquivo completo pelo número de linha antes de publicar** — a extração é automática.
- **O dado citado leva link para o PDF público** do estudo:
  `https://metakosmos.com.br/api/media/file/State%20of%20Immersive%20%26%20Agentic%20Commerce%202026%20powered%20by%20mK.pdf?prefix=prod%2Fsite`
- **Mínimo 1 CTA para o estudo**, apontando para `https://metakosmos.com.br/estudo`
  (página com captura de lead). O CTA do estudo é **adicional** ao CTA final de contato, não substitui.
- **UTMs obrigatórios** nos dois links, conforme `utm-tracking.md`:
  - citação no corpo → `utm_source=blog&utm_medium=cta-inline&utm_campaign=state-of-immersive-agentic-commerce-2026`
  - CTA → `utm_source=blog&utm_medium=cta-final&utm_campaign=state-of-immersive-agentic-commerce-2026`
- **Não inventar dado do estudo.** Se o índice não tiver número que sustente o argumento, buscar
  outra seção ou usar outro dado. Número sem origem no estudo é falha bloqueadora.

### Tamanho e Estrutura do Texto
- **Mínimo 2000 palavras** por artigo (piso absoluto — override em qualquer pedido menor, avisando o usuário)
- **Parágrafos de 35-40 palavras no máximo** (piso duro)
- **FAQ com mínimo 10 perguntas** (H3 pergunta + parágrafo resposta), respondendo dúvidas reais de busca e LLMs
- Respostas de FAQ: **60-90 palavras cada**, autossuficientes, **primeira frase respondendo direto à pergunta**

### Formato (Payload — ver output-payload.md)
- Escrever em **HTML semântico simples**: `<h1>` (título), `<h2>`/`<h3>`/`<h4>`, `<p>`, `<strong>`, `<em>`, `<u>`, `<ul>/<ol>+<li>`, `<a href>`, `<img>`, `<hr>`, `<blockquote>`.
- **NÃO usar:** `<div>` de card/coluna, `style=` (font-size NÃO renderiza), classes `wp-block-*`, botões, cores de fundo, spacers, comentários `<!-- wp:* -->`, `<table>` complexa.
- **Sem sumário/ToC** (o Payload gera o "Conteúdo" automaticamente a partir dos seus headings — então quebre bem).

### Estrutura mais granular (regra reforçada)
- **Quebrar o conteúdo fino em h2 / h3 / h4.** Cada H2 com 2-4 subitens (H3), e H3 longos em H4. Evitar blocos de texto corrido: nenhuma seção deve passar de ~3 parágrafos sem um heading, lista, caixa ou imagem.

### Ênfase e escaneabilidade (regra reforçada — evitar "texto corrido")
- **Aumentar a densidade de destaques.** Meta: cada parágrafo relevante tem ao menos 1 trecho em **negrito**; usar **itálico** e **sublinhado** (`<u>`) para variar a ênfase. Números e stats sempre destacados.
- **Caixa de destaque = `<blockquote>`** (renderiza como box). Usar para stats, provocações, definições e callouts — meta 2-4 por artigo. Ex: `<blockquote><p><strong><u>+94% de conversão</u></strong> ...</p></blockquote>`.
- **NÃO simular componentes do Gutenberg** (número gigante, card colorido, botão): não renderizam e confundem. O destaque vem de negrito/itálico/sublinhado + caixa quote + headings + listas + imagens.

### Cores e Marca
- O Brand Book (`[mK] Brand Book.txt`) vale como referência de **voz e tom**. As **cores NÃO se aplicam** ao corpo (não há blocos coloridos). Não escrever cor no HTML.

### Imagens (ver media-payload.md)
- **Aumentar a incidência de imagens/gifs/gráficos** — meta 1 a cada 2-3 seções, distribuídas no fluxo. Escolher SÓ nomes que existem em `references/media-payload.md`.
- **Nenhuma imagem flutua em coluna lateral.** Verificado no CSS do tema em 18/08/2026: a regra
  `.blog-post-inline-img` é `display:block; margin:auto` e **não existe uma única declaração `float:`
  em todo o CSS do blog**. O nó `upload` do Lexical até tem a propriedade `format` (o campo de
  alinhamento padrão), mas o frontend a ignora: emite sempre a mesma classe. Coluna lateral só
  passa a existir com mudança no tema.
- **A orientação muda o tamanho, não o alinhamento:**
  - **Horizontal** → ocupa a largura inteira do conteúdo (`max-width:100%`). É o formato a preferir.
  - **Vertical** → não vai para a lateral; renderiza **centralizada e estreita**, porque a altura é
    limitada a `min(50vh, 520px)` e a largura encolhe junto. Usar só quando o conteúdo da imagem
    exigir, ciente de que ela ocupa pouca área.
- **Hero → featuredImage:** a 1ª imagem antes do 1º parágrafo vira a imagem destacada (e sai do corpo). Escolher uma imagem **horizontal** do catálogo — como vem da Media, a featuredImage é preenchida automaticamente.
- Todo `<img>` com `alt` descritivo. Sem `style=`.

### Links e UTMs
- Mínimo 6-8 links internos, todos verificados (`sitemap-urls.md` / `blog-links.md`), com UTMs completos (`utm-tracking.md`).
- No HTML pode usar `&amp;` entre parâmetros (o conversor decodifica para `&`). Preferir **URLs relativas** no padrão Payload (`/mk3d`, `/blog/[slug]`, `/mkases/[slug]`) — atenção a slugs que mudaram do WP para o Payload.
- Regra "first mention link": marca-cliente citada pela 1ª vez → `/mkases/[slug]`; solução mK citada pela 1ª vez → LP correspondente.
- **O tema TRANSFORMA em botão rosa, sozinho, todo link para `form.respondi.app`.** Verificado em
  18/08/2026: a classe `btn btn-pink` é aplicada pelo frontend a partir da URL, não vem do HTML nem
  fica salva no Lexical. Vale para todos os posts. Consequência prática:
  - **Link de formulário NUNCA no meio de uma frase.** Botão rosa brotando entre duas vírgulas fica
    horrível. O link vai **sozinho no seu próprio `<p>`**.
  - O parágrafo anterior prepara o clique e termina com **"clique no botão abaixo"** (ou equivalente).
  - **Um botão por artigo**, no CTA final. Dentro de FAQ, seção intermediária ou resposta curta,
    nada de link de formulário: cita "falar com um mentor da metaKosmos" em texto puro, sem link.
  - Padrão correto:
    `<p>...Para começar, <strong>clique no botão abaixo</strong>.</p>`
    `<p><a href="https://form.respondi.app/...">Fale com um mentor da metaKosmos</a></p>`
- Demais CTAs viram parágrafo com link comum (o Payload não tem componente de botão). Links que não
  são do `form.respondi.app` — inclusive o do estudo — renderizam como texto e podem ficar inline.

---

## Fluxo de Criação (10 passos)

Igual à blog-mk, com o passo de formatação final adaptado:

1. **Input do usuário** — título (mínimo) ou pauta (ideal).
2. **Pesquisa e leitura de referências** — carregar TODAS; WebSearch p/ dados externos; consultar sitemap/blog-links/media.
   **Passar pelo `estudo-indice.md` e escolher o(s) dado(s) do estudo que vão sustentar o artigo**,
   anotando o número da linha para conferir no arquivo completo antes de publicar.
3. **Pauta** (gera Documento 1) — template de `processo-pauta.md`: H1, tipo de abertura, 8-12 H2s, direcionamento por H2, mKases (mín 2), links internos (mín 4-8, verificados), mídias reais, 10+ FAQ, marcas→mkases, soluções→LP. **H1 abrindo pela keyword exata** e
   **dado(s) do estudo escolhidos, com número da linha de origem.**
4. **Escrita em chunks de 1000 palavras** — cobrir 3-4 H2s por chunk, revisar tom/voz/parágrafos/negrito a cada chunk.
5. **Integração** — juntar chunks, checar fluxo, transições orgânicas, sem repetição, total ≥ 2000 palavras.
6. **Auditoria de texto** — checklist 30 itens de `anti-ia-rules.md`; corrigir padrões de IA, parágrafos >40 palavras, aberturas proibidas, afirmações sem dado.
7. **Revisão editorial** — marcar negritos, onde entram imagens (nomes reais da Media), citações, posição de links e CTAs.
8. **Formatação final em HTML semântico** (gera Documento 2) — construir `artigo.html` conforme `output-payload.md`:
   - Só tags semânticas permitidas; sem chrome visual, sem `style=`/font-size.
   - Estrutura granular **h2/h3/h4**; nenhuma seção com >3 parágrafos corridos.
   - Ênfase densa: **negrito/itálico/sublinhado** + **caixas `<blockquote>`** (2-4) para stats/callouts.
   - `<h1>` no topo (vira título); hero = 1ª `<img>` **horizontal** do catálogo (vira featuredImage); sem ToC.
   - Imagens distribuídas (1 a cada 2-3 seções), SÓ nomes de `media-payload.md`; links com UTMs.
   - Rodar a **auditoria de formato + anti-IA programática** (abaixo) e corrigir.
9. **Entrega** — Pauta, Artigo e Metadados + Completion Summary.
10. **Publicação (automática, sem perguntar) — NESTA ORDEM:**
    ```bash
    # a) artigo AO VIVO no blog (padrão do usuário desde 02/09/2026)
    python scripts/payload_publish.py <slug> --status published

    # b) escrever output/[slug]/linkedin.md conforme references/linkedin-post.md

    # c) post AO VIVO na página da metaKosmos (o link já está no ar por causa do passo a)
    python scripts/linkedin_publish.py <slug>

    # d) manter as listas em dia
    python scripts/status_backlog.py
    python scripts/sync_payload_lists.py
    ```
    **A ordem importa.** Publicar o artigo primeiro é o que faz o link do LinkedIn nascer
    funcionando. Invertida, todo post nasce em 404. Por isso o `linkedin_publish.py` roda
    aqui **sem** `--skip-link-check`: a verificação de HTTP 200 agora vale como conferência
    real de que o artigo subiu antes do post sair.
    - **Ambos saem ao vivo e públicos**, sem etapa de revisão humana. Decisão do usuário,
      tomada com os riscos na mesa. Isso torna a auditoria do passo 8.5 a **única** rede
      de proteção antes do público: nenhum bloqueador dela pode ser relevado.
    - **Rodar o LinkedIn UMA vez.** Ele não deduplica. O primeiro disparo bem-sucedido grava
      `output/[slug]/.linkedin-posted.json` e a trava recusa os seguintes, mas não conte
      com ela para consertar descuido: ela existe para o re-run acidental.
    - Se a validação do LinkedIn reprovar, corrigir o `linkedin.md` e rodar de novo sem
      `--force` (nada foi postado, não há duplicata a temer).

### Auditoria de formato (passo 8.5 — OBRIGATÓRIO, cada item BLOQUEADOR)

**Título e estudo (checar primeiro):**
0a. **Keyword exata na abertura do H1**, sem paráfrase, sem sinônimo, complemento sem eco.
    Keyword também no 1º parágrafo e em ao menos um H2/FAQ. Título SEO do metadados ≤60c abrindo pela keyword.
0c. **Botão isolado:** nenhum link para `form.respondi.app` no meio de frase. O link do formulário
    está sozinho num `<p>`, o parágrafo anterior chama o clique, e há no máximo 1 no artigo inteiro.
0b. **Estudo citado:** há ≥1 dado do State of Immersive & Agentic Commerce 2026 no corpo, com link
    para o PDF (UTM `cta-inline`), e ≥1 CTA para `/estudo` (UTM `cta-final`). Dado conferido na linha
    de origem do arquivo completo.

**Formato Payload:**
1. **Sem tags proibidas:** nenhum `<div>` de card/coluna, `style=` (nem font-size), classe `wp-block-*`, `<button>`, comentário `<!-- wp:* -->`. Buscar e remover.
2. **HTML bem-formado:** cada `<p>`, `<h2>`, `<ul>`, `<li>`, `<a>`, `<blockquote>` aberto tem fechamento. `<img>`/`<hr>` self-closing ou simples.
3. **1 único `<h1>`** no topo; nenhum outro `<h1>` no corpo.
4. **Imagens no catálogo:** todo `<img>` tem `alt` e um `src` cujo nome existe em `media-payload.md` (o publicador remove os que não existem). Hero horizontal.
5. **Granularidade e ênfase:** há h3/h4 (não só h2); há ≥2 caixas `<blockquote>`; nenhuma seção com >3 parágrafos sem heading/lista/caixa/imagem.

**Anti-IA programática (contagens duras — iguais à blog-mk):**
5. **Em dashes (—):** contar no HTML completo (corpo + FAQ + alt). **Limite: 0.** Substituir por vírgula, parênteses, dois pontos ou nova frase.
6. **"Não é X, é Y":** limite 2 no artigo inteiro.
7. **Anáfora staccato / frases curtas sem conector:** zero anáfora; máx 1 frase-parágrafo isolada como recurso.
8. **Frases-conclusão** ("em conclusão", "em resumo", "por fim", "em suma", etc.): **limite 0.**
9. **Limites SEO (no metadados):** Título SEO ≤60c; Meta Description ≤155c.

Reportar contagens reais no documento de metadados. Corrigir e re-rodar antes de entregar.

---

## Guardrails

### NUNCA
- Escrever componentes Gutenberg/visuais (cards, colunas, botões, cores de fundo, spacers, número gigante via font-size) — não renderizam e confundem.
- Usar `<div>`, `style=` (font-size NÃO renderiza), classes `wp-block-*` ou comentários `<!-- wp:* -->` no `artigo.html`.
- Tentar colocar imagem em coluna lateral. O CSS do tema não tem nenhuma regra `float:` e o frontend
  ignora o `format` do nó `upload`. Vertical não vai para a lateral: sai centralizada e estreita.
- Referenciar imagem que não está em `media-payload.md`.
- **Parafrasear a keyword-alvo no `<h1>`** ou trocá-la por sinônimo. Ela entra exata e na abertura.
- **Escrever complemento de título que apenas repete a keyword** ("X: sobre X").
- **Entregar artigo sem citação do estudo** ou sem CTA para `/estudo`.
- **Colocar link do `form.respondi.app` no meio de um parágrafo.** O tema vira botão rosa e o
  resultado fica quebrado. Botão sempre sozinho, chamado pelo parágrafo anterior.
- **Inventar número e atribuir ao estudo.** Todo dado sai do `estudo-indice.md` e é conferido na origem.
- Usar aberturas proibidas ("Imagine que...", "Neste artigo vamos...", "Em um mundo cada vez mais...").
- Usar vocabulário de IA ("Adicionalmente", "panorama", "alavancar", "sinergia", "holístico", "multifacetado").
- Usar **qualquer em dash (—)** no artigo inteiro.
- Usar frases-conclusão formulaicas.
- Escrever parágrafos com mais de 40 palavras.
- Incluir sumário/ToC (Payload gera).
- Entregar Título SEO >60c ou Meta Description >155c.
- Entregar artigo com menos de 2000 palavras ou FAQ com menos de 10 perguntas.
- Inventar URLs ou cores; linkar concorrentes.
- Referenciar imagem que não existe na Media do Payload sem sinalizar.

### SEMPRE
- Carregar todas as referências antes de escrever (incluindo `output-payload.md` e `estudo-indice.md`).
- **Keyword-alvo exata abrindo o H1**, no 1º parágrafo e em um H2/FAQ.
- **Citar o estudo com link para o PDF + CTA para `/estudo`**, ambos com UTM.
- Gerar os 4 documentos (Pauta + Artigo + Metadados + LinkedIn).
- Artigo em `artigo.html` como **HTML semântico simples**.
- Mínimo 2000 palavras; parágrafos 35-40 palavras; FAQ 10+ perguntas.
- Mínimo 2 mKases com métricas reais; 6-8 links internos verificados com UTMs.
- Responder a pergunta principal nos primeiros 150 palavras (GEO); "metaKosmos" associada a resultado ≥3 vezes.
- Storytelling sensorial da Lara; 1 "Spoiler:", parênteses coloquiais, 1 frase-parágrafo isolada.
- Rodar auditoria de formato + anti-IA programática antes da entrega.
- Metadados SEO vão no Documento 3 (não no artigo).

### PARAR quando
- Tema fora dos 7 pilares sem confirmação.
- Falha em item [BLOQUEADOR] da self-audit.
- Faltam dados/estatísticas reais (não inventar).

---

## Detecção Automática de Modo

| Input fornecido | Modo |
|----------------|------|
| Keyword + pilar + pedido de pauta/briefing | **Pautar** |
| Título + briefing/keywords (ou só ideia) | **Gerar** |
| Texto de artigo + pedido de melhoria | **Reescrever** |
| Texto de artigo + "limpar"/"humanizar" | **Humanizar** |
| Texto de artigo + "avaliar"/"auditar"/"score" | **Auditar** |
| "publica [slug]" / "sobe pro Payload" / "manda pro site" + slug em `output/` | **Publicar** |
| "post do LinkedIn" / "gera o LinkedIn de [slug]" / "posta no LinkedIn" | **LinkedIn** |

Os modos Pautar/Gerar/Reescrever/Humanizar/Auditar seguem a mesma lógica da skill blog-mk (mesmos passos e critérios editoriais), com a única diferença de que o Documento 2 é **HTML semântico** (não Gutenberg). Consultar a skill original para os detalhes de cada modo; as regras de conteúdo são idênticas.

---

## Modo Publicar (envia para o Payload, ao vivo por padrão)

### Quando usar
"publica [slug]", "sobe o artigo pro Payload", "manda pro site", com o artigo já em `output/[slug]/` (mín. `artigo.html` + `metadados.md`).

### O que faz — `scripts/payload_publish.py`
1. **Converte** `artigo.html` (HTML semântico) → **Lexical JSON**.
2. **Autentica** no Payload via `POST /api/users/login` (email/senha do `.env`) → header `Authorization: JWT <token>`.
3. Extrai **título** (do `<h1>`), **excerpt** (1º parágrafo).
4. Resolve **categoria** pelo **pilar** do metadados (`PILAR_TO_CATEGORY_SLUG`) → mapa de nomes → slugify; lookup em `/api/categories`.
5. Resolve **tags** por slug em `/api/tags`; **cria** as que faltam (com `title` + `slug`).
6. Resolve **imagens inline** por nome de arquivo em `/api/media` → nós `upload` por ID; remove as não encontradas (com aviso).
7. Define **featuredImage** pela hero (1ª imagem), se existir na Media.
8. Cria o post via `POST /api/posts?locale=pt-BR&draft=true` com `_status:"draft"`, SEO (`metaTitle`/`metaDescription`/`noIndex`), categoria, tags.
9. Reporta ID e URL do editor.

### Depois de publicar — manter as listas atualizadas (OBRIGATÓRIO, sem perguntar)
Ao final de cada publicação (rascunho ou live), rode nesta ordem — são chamadas leves
e paginadas contra a API do Payload, não precisam de agendamento externo:
```bash
python scripts/status_backlog.py       # cruza BACKLOG-EDITORIAL.md com o que existe no Payload
python scripts/sync_payload_lists.py   # atualiza blog-links.md (artigos) e mkases.md (mKases)
python scripts/sync_payload_media.py   # só se mídia nova foi enviada nesta sessão
```
Se estiver publicando **vários artigos em lote na mesma sessão**, rode os três só ao
final do lote (não a cada artigo individual) para evitar chamadas redundantes.

### Comandos
```bash
python scripts/payload_publish.py --list                    # lista slugs em output/ (inclui Postado/)
python scripts/payload_publish.py <slug> --dry-run          # converte e salva o Lexical, SEM API
python scripts/payload_publish.py <slug> --probe            # testa login + coleções
python scripts/payload_publish.py <slug>                    # cria rascunho (default do script)
python scripts/payload_publish.py <slug> --status published # AO VIVO (é o que a skill usa)
```

### Requisitos (`.env` em `blog mK Payload/.env`)
```
PAYLOAD_API_URL=https://metakosmos.com.br
PAYLOAD_EMAIL=...
PAYLOAD_PASSWORD=...
# opcionais: PAYLOAD_AUTH_COLLECTION, PAYLOAD_AUTH_SCHEME, PAYLOAD_API_KEY
```

### Padrões fixos
- **Status: AO VIVO por padrão** (`--status published`), desde 02/09/2026, a pedido do usuário.
  O flag `--status draft` continua existindo para quando o artigo precisar de revisão antes.
  O default do *script* continua `draft` de propósito: quem decide publicar ao vivo é a skill,
  passando o flag, e não um script rodado sem querer.
  Consequência: **não existe mais revisão humana entre a geração e o público.** A auditoria
  do passo 8.5 vira a única rede, e cada bloqueador dela passa a valer por uma revisão.
  A regra de "testar em 1 antes de qualquer massa" continua valendo para publicação em lote.
- **Autor:** por padrão sem autor (posts do Payload aceitam `author: null`). Ajustar se o time definir um autor fixo.
- **Categoria por pilar** (mapa em `PILAR_TO_CATEGORY_SLUG`): 1→immersive-commerce, 2→provador-virtual, 3→visualizador-3d-ar, 6→mkcases-tag.
- **featuredImage** só é definida se a hero existir na Media; senão, definir no admin.

### i18n PT/EN/ES
O post é criado em `pt-BR`. Para EN/ES, os campos localizados são salvos **um locale por vez**: após criar, `PATCH /api/posts/<id>?locale=en` (e `es`) com as traduções. (Passo de tradução ainda a automatizar — ver Pendências.)

---

## Modo LinkedIn (gera o post e publica na página da metaKosmos)

### Quando usar
**Geração e publicação rodam sozinhas no passo 10** do fluxo, ao fim de todo artigo novo,
sem perguntar. O post entra ao vivo na página da metaKosmos na hora.

Sob demanda também: "gera o post de LinkedIn de [slug]", "posta no LinkedIn",
"reposta com --force". Pressupõe o artigo já em `output/[slug]/`.

### O que faz
1. Lê `artigo.html` e `metadados.md` do slug e escreve **`output/[slug]/linkedin.md`** (4º documento, gerado sob demanda).
2. Segue **`references/linkedin-post.md`** à risca: gancho de até 100 caracteres, linha
   `Leia completo em: <url>` imediatamente depois, corpo em 3 ou 4 blocos com pelo
   menos um número, e 3 a 5 hashtags.
   **Alvo de 900 a 1.400 caracteres (~150 a 230 palavras), teto de 1.800.**
   Atenção: a medida é em **caracteres**, não em palavras.
   O post é **teaser, não resumo**: abre a lacuna e para. Se ele responder a pergunta que
   levantou, o leitor não tem motivo para clicar. Convencer é trabalho do artigo.
3. `scripts/linkedin_publish.py` valida (bloqueadores) e dispara um **webhook do Make**,
   que posta pelo módulo **LinkedIn v2 › Create a Company Text Post** (`CreateTextShare`),
   `visibility=PUBLIC`, `feedDistribution=MAIN_FEED`.

### Por que Make e não API da LinkedIn direto
Postar em página de empresa pela API exige o produto **Community Management API**
(app próprio, aprovação manual da LinkedIn, token de 60 dias para renovar). O Make já é
parceiro aprovado, a conexão LinkedIn da metaKosmos já existe na conta e o módulo v2 não
tem limite de caracteres (o v1, `ActionCreateCompanyShare`, trava em 700 e **não serve**).
Custo de manutenção zero. Se um dia a LinkedIn aprovar um app próprio, o ponto de troca é
só a função `post_to_make()`.

### Comandos
```bash
python scripts/linkedin_publish.py --list                    # slugs com linkedin.md pronto
python scripts/linkedin_publish.py <slug> --check            # só valida, não envia
python scripts/linkedin_publish.py <slug> --dry-run          # valida e mostra o corpo
python scripts/linkedin_publish.py <slug>                    # POSTA na página
python scripts/linkedin_publish.py <slug> --skip-link-check  # pula o HTTP na URL
```

### Bloqueadores automáticos (o script recusa postar)
Tamanho fora de 500 a 1.800 caracteres · gancho acima de 100 caracteres · a linha
`Leia completo em:` fora da linha 3 · número de URLs diferente de 1 · UTM faltando ou
errado · em dash · abertura ou frase-conclusão proibida · `**` de markdown · emoji ·
valor monetário · nenhum número no corpo · hashtags fora de 3 a 5.

Avisos, que **não** bloqueiam: URL respondendo 404 (o artigo pode entrar no ar depois),
vocabulário de IA, anáfora staccato, gancho em pergunta.

### Padrões fixos
- **Gerar E postar, ambos automáticos** no fim de todo artigo (passo 10), sem perguntar.
  Ao contrário do blog, que sobe como rascunho, o LinkedIn não tem rascunho por API: o post
  nasce ao vivo e público na página. O usuário optou por isso sabendo do risco (02/09/2026).
- **Uma vez por slug.** O LinkedIn não deduplica, então o primeiro disparo bem-sucedido
  grava `output/[slug]/.linkedin-posted.json` e a trava recusa os próximos. `--force`
  contorna, e só deve ser usado se o usuário pedir repost explicitamente.
- **Se algo der errado depois do post**, o conserto é no LinkedIn (apagar o post na página),
  não no script. Apagar o marcador sem apagar o post gera duplicata no próximo disparo.
- **Um link por post**, sempre com `utm_source=linkedin-organico&utm_medium=organic-social`.
- **O artigo não precisa estar no ar** para o post sair. O script avisa se a URL responde
  404 e posta assim mesmo, por decisão do usuário: o artigo entra no ar em algum momento e
  o link passa a funcionar sozinho. Só vale publicar o artigo no mesmo dia, para encurtar
  a janela em que o clique cai em 404.
- **Sem valor monetário**, igual ao blog.

### Requisitos (`.env`)
```
LINKEDIN_WEBHOOK_URL=https://hook.us1.make.com/xxxxxxxx
# opcionais: LINKEDIN_ORG_URN, LINKEDIN_LINK_PREFIX, LINKEDIN_MAX_CHARS, LINKEDIN_MIN_CHARS
```

### Cenário do Make (já criado em 02/09/2026)

| Item | Valor |
|---|---|
| Cenário | `[mK] Blog -> LinkedIn (pagina metaKosmos)` — ID **4901009** |
| Organização / Time | 704086 / 279448 (`[MKO] @metakosmoslab` / My Team) |
| Webhook | ID 2811924 — a URL vive em `LINKEDIN_WEBHOOK_URL` no `.env`, **nunca aqui** (quem tem a URL posta na página) |
| Módulo 2 | `linkedin:CreateTextShare` v2, `content={{1.content}}`, `type=text`, `visibility=PUBLIC`, `feedDistribution=MAIN_FEED` |
| Estado | **inativo**, com dois campos pendentes de configuração manual |

Pendências de uma vez só, no Make:
1. **Reconectar o LinkedIn.** A conexão `[MKL] metaKosmos (Patrick)` (ID 4397662, tipo
   `linkedin-openid`, aceita pelo módulo v2) **expirou em 06/08/2026**. Precisa dos escopos
   `w_organization_social` e `rw_organization_admin`, e o usuário conectado precisa ser
   **admin da página** da metaKosmos.
2. **Escolher a Company** no dropdown do módulo 2 (campo `organization`, ficou vazio porque
   é preenchido por RPC autenticado).
3. **Ativar** o cenário.

Se preferir fixar a página pelo `.env` em vez do dropdown, setar `LINKEDIN_ORG_URN=urn:li:organization:<id>`
e mapear `organization` para `{{1.organization}}` no módulo.

---

## Capacidades do editor Lexical (comprovado em teste, 2026-07; imagens reverificadas em 2026-08)
- **Renderiza:** h2/h3/h4/h5, negrito, itálico, **sublinhado**, **quote (caixa de destaque)**, imagens, links, `<hr>`, bloco `embed` (vídeo).
- **NÃO renderiza:** font-size inline (número grande), imagem flutuada em coluna, cor de fundo, botão/card/stat nativo. O ToC ("Conteúdo") é gerado pelo frontend a partir dos headings.
- **Nós Lexical em uso no blog inteiro** (varredura dos 40 posts, 08/2026): `text` (11.836), `paragraph` (1.767),
  `heading` (1.082), `listitem` (448), `link` (351), `quote` (281), `horizontalrule` (188), `upload` (120), `list` (104).
  Nenhum bloco customizado. O `upload` carrega `format` (alinhamento) em todos os 120 casos, sempre vazio e sempre ignorado pelo tema.
- **Para habilitar imagem em coluna lateral seria preciso mexer no frontend:** emitir uma classe a partir do
  `format` do nó `upload` e criar a regra de `float` correspondente. Hoje nada disso existe.

## Pendências conhecidas
- **featuredImage:** ✅ resolvida — hero sai do catálogo `media-payload.md`, então sempre existe na Media.
- **Sync de mídias:** ✅ `scripts/sync_payload_media.py` gera `media-payload.md` de `/api/media`.
- **Sync de links internos:** `blog-links.md` ainda é do WP. Portar para `/api/posts` do Payload (slugs `/blog/[slug]`, `/mkases/[slug]`).
- **i18n EN/ES:** automatizar tradução + `PATCH ?locale=en|es`.
- **URLs internas:** normalizar para relativas e remapear slugs que mudaram (ex: `/mk-3d-shop/` → `/mk3d`).
- **Modo `--update <id>`:** editar post existente em vez de criar novo.

---

## Completion Summary

```
+====================================================+
| ENTREGA: Blog mK (Payload) — [Título]             |
+====================================================+
| Modo:          [Pautar/Gerar/Reescrever/Hum/Aud]  |
| 📂 Pasta:      output/[slug]/                      |
| 📋 pauta.md  📝 artigo.html  📊 metadados.md       |
| 💼 linkedin.md ([N] caracteres)                    |
+----------------------------------------------------+
| Palavras: [N] | FAQ: [N] | mKases: [N]            |
| Keyword no H1: [exata/FALHA] | 1º parágrafo: [ok] |
| Estudo: [N dados citados] | CTA /estudo: [ok]     |
| Links UTM: [N verificados] | Imagens: [N]         |
| Formato: HTML semântico (→ Lexical) OK            |
| Anti-IA: em dash [0] | conclusão [0] | staccato OK |
| GEO/AEO: [Conforme / pendências]                  |
+----------------------------------------------------+
| ARTIGO:   AO VIVO em /blog/[slug] | ID [N]        |
| LINKEDIN: POSTADO em [data/hora]  | link 200 [ok] |
| Listas sincronizadas: backlog + links             |
+====================================================+
```
