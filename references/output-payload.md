# Output para Payload CMS — formato do artigo

Esta skill NÃO gera Gutenberg Block Markup. O CMS agora é **Payload**, cujo campo `content` é uma árvore **Lexical (JSON)**. O `payload_publish.py` faz a conversão automática, então o artigo é escrito em **HTML semântico simples** (`output/[slug]/artigo.html`) e o script traduz para Lexical na publicação.

## Regra de ouro: Payload é "plano" (mas com recursos de destaque)

O Lexical de vocês usa **apenas primitivos** (fora o bloco `embed` para vídeo). Não há bloco de card/stat/caixa. Tudo que é "chrome visual" do Gutenberg (cards coloridos, botões, colunas 50/50, stat boxes, cores de fundo, spacers) **é achatado ou não renderiza**. **Não escreva esses componentes.**

### O que RENDERIZA de verdade (comprovado em teste no frontend)
- **Headings h2, h3, h4** — quebrar o conteúdo fino (o sumário do site é montado a partir deles).
- **Negrito** (`<strong>`), **itálico** (`<em>`) e **sublinhado** (`<u>`) — todos renderizam. Usar com generosidade para escanear.
- **Bloco de citação** (`<blockquote>`) — renderiza como **CAIXA de destaque** visualmente diferente. **Este é o jeito de fazer "caixa de destaque"** (stat, provocação, definição, callout).
- **Imagens** e **links**.
- **Linha** (`<hr>`) entre seções.

### O que NÃO renderiza (NÃO usar — vira confusão)
- **Mudança de tamanho de fonte** (font-size inline): persiste no dado mas o tema **não renderiza**. **Não** tente fazer "número grande". Para destacar um stat, use uma **caixa quote** com o número em **negrito + sublinhado**.
- **Imagem em coluna lateral** (float): o tema **não** flutua imagem. **Toda imagem é full-width**, seja vertical ou horizontal. Não tente colocar imagem ao lado de texto.
- Cores de fundo, botões, cards, spacers, tabelas complexas.

### Como destacar um número/stat (substitui o "número grande" do Gutenberg)
```html
<blockquote><p><strong><u>+94% de conversão</u></strong> em marcas que adotam visualizador 3D com AR, com dado auditado e nome de cliente.</p></blockquote>
```

## HTML que o conversor entende (use SÓ estas tags)

| Tag HTML | Vira no Lexical | Observação |
|---|---|---|
| `<h1>` | **título do post** (sai do corpo) | 1 por artigo, no topo |
| `<h2>`, `<h3>`, `<h4>` | `heading` | estrutura das seções — **quebrar fino** |
| `<p>` | `paragraph` | corpo (35-40 palavras máx.) |
| `<strong>` / `<b>` | texto `format:1` (bold) | ênfase — usar com generosidade |
| `<em>` / `<i>` | texto `format:2` (itálico) | ênfase |
| `<u>` | texto `format:8` (sublinhado) | ênfase — **renderiza** |
| `<ul>` / `<ol>` + `<li>` | `list` (bullet/number) + `listitem` | listas |
| `<a href>` | `link` (linkType custom, newTab) | UTMs no href; `&amp;` é ok (o conversor decodifica p/ `&`) |
| `<img src>` | `upload` (referência à Media por ID) | ver "Imagens" abaixo — **full-width** |
| `<hr>` | `horizontalrule` | separador entre seções |
| `<blockquote>` | `quote` | **CAIXA de destaque** (renderiza como box) |
| `<figure><figcaption>` | imagem + parágrafo de legenda | opcional |

**NÃO use:** `<div>` de card/coluna, `style=`, classes `wp-block-*`, botões, cores de fundo, `<table>` complexa (vira texto), comentários `<!-- wp:* -->`. Se aparecerem, o conversor achata ou descarta — melhor não gastar tokens escrevendo.

## Imagens

- **Fonte única: `references/media-payload.md`** — catálogo real das 352 mídias do Payload (gerado por `scripts/sync_payload_media.py`). Referencie a imagem pelo **nome de arquivo exato** da coluna `filename`. Só use nomes que aparecem no catálogo — imagens sem correspondência são **removidas do corpo** na publicação.
- **Aumente a densidade de imagens:** distribua imagens/gifs/gráficos ao longo do artigo (meta: 1 a cada 2-3 seções). Escolha por tema no `alt` do catálogo.
- **Todas full-width.** O tema NÃO flutua imagem em coluna — não importa orientação. Não escreva imagem ao lado de texto.
- **Hero → featuredImage:** a **1ª imagem antes do 1º parágrafo** vira a imagem destacada (e sai do corpo). Escolha uma imagem **horizontal** do catálogo (melhor para banner). Como sai do catálogo, ela sempre existe na Media e a featuredImage é preenchida automaticamente.
- Todo `<img>` precisa de `alt` descritivo.

## Links e UTMs

- Todos os links internos com UTMs completos (ver `utm-tracking.md`). No HTML pode escrever `&amp;` entre parâmetros (HTML válido); o conversor decodifica para `&` no Lexical, que é como o Payload armazena.
- URLs: **preferir relativas** no padrão Payload (ex: `/mk3d`, `/blog/[slug]`, `/mkases/[slug]`). O site novo usa slugs diferentes do WP em alguns casos (ex: `/mk-3d-shop/` no WP → `/mk3d` no Payload). Verificar em `sitemap-urls.md` / `blog-links.md`.

## Exemplo mínimo de `artigo.html`

```html
<h1>Título do Artigo com Keyword</h1>

<img src="hero-real-da-media.gif" alt="descrição da hero">

<p>Primeiro parágrafo respondendo a pergunta principal, com <strong>trecho em negrito</strong> e um <a href="/mk3d?utm_source=blog&amp;utm_medium=internal-link&amp;utm_campaign=pilar3-visualizador-3d-ar&amp;utm_content=slug">link interno</a>.</p>

<h2>Primeira seção como pergunta</h2>
<p>Parágrafo curto e direto.</p>
<ul>
  <li><strong>Item:</strong> explicação.</li>
  <li><strong>Item:</strong> explicação.</li>
</ul>

<img src="imagem-inline-da-media.png" alt="descrição">

<hr>

<h2>Próxima seção</h2>
<p>...</p>
```

## Publicação

`python scripts/payload_publish.py <slug>` — cria rascunho no Payload. Ver a seção "Modo Publicar" da SKILL.md para o fluxo completo (auth, categoria por pilar, tags, i18n).
