# Post de LinkedIn — regras editoriais (Modo LinkedIn)

Regras do post orgânico da **página da metaKosmos** gerado a partir de um artigo do blog.

**O post é teaser, não resumo.** Ele não tenta entregar o argumento do artigo em versão
comprimida. Ele abre uma lacuna e para. Quem quer fechar a lacuna clica. Se o post
respondeu a pergunta que levantou, ele fracassou: o leitor já tem o que queria e não vai
ao blog. O trabalho de convencer é do artigo, que tem 2.000 palavras para isso.

Publicação: `scripts/linkedin_publish.py` → webhook do Make → módulo
**LinkedIn v2 › Create a Company Text Post** (`CreateTextShare`), `visibility=PUBLIC`,
`feedDistribution=MAIN_FEED`.

---

## Arquivo de saída

Um por artigo, ao lado dos outros três documentos:

```
output/[slug]/
├── pauta.md
├── artigo.html
├── metadados.md
└── linkedin.md      ← este
```

Formato do `linkedin.md` (o script lê o corpo depois do primeiro `---` isolado):

```markdown
# LinkedIn — [slug]

**Página:** metaKosmos
**Artigo:** https://metakosmos.com.br/blog/[slug]
**Caracteres:** [N]
**Pilar:** [N]

---
[texto do post, exatamente como vai para o LinkedIn]
```

Tudo acima do `---` é cabeçalho de controle e **não** vai para o LinkedIn.
Tudo abaixo vai literal, com as quebras de linha preservadas.

---

## Estrutura obrigatória (nesta ordem)

1. **Gancho** — 1 linha, até 100 caracteres. É o que aparece antes do "…ver mais".
   Afirmação ou dado, nunca pergunta retórica e nunca hashtag.
2. **Linha em branco.**
3. **Chamada do link**, sempre no mesmo formato:
   `Leia completo em: <url do artigo com UTM>`
   Essa linha é fixa por decisão do usuário: o link vem logo depois do gancho, não no fim.
4. **Linha em branco.**
5. **Corpo** — **3 ou 4 blocos de 1 a 3 linhas**, separados por linha em branco.
   Um bloco = uma ideia. Sem bullets, sem numeração, sem mini-header.
   Pelo menos um bloco carrega **um número** (do *State of Immersive & Agentic Commerce 2026*
   ou do próprio artigo), porque número é o que cria a curiosidade.
   Puxar de `estudo-indice.md` e conferir na fonte. Número inventado reprova.
6. **Hashtags** — 3 a 5, na última linha, sem acento e sem espaço.

CTA final é **opcional e raro**. O link já é o CTA, e uma pergunta no fim compete com ele
pela atenção. Só usar quando a pergunta for melhor gancho de comentário do que o artigo é
de clique, e nunca as duas coisas no mesmo post.

---

## Tamanho

**As medidas aqui são em CARACTERES, não em palavras.** Como referência rápida:
900 a 1.400 caracteres é mais ou menos **150 a 230 palavras**, ou seja, um post que
ocupa a tela do celular e pede um "…ver mais".

| Medida | Valor |
|---|---|
| Alvo | **900 a 1.400 caracteres** (~150 a 230 palavras) |
| Piso | 500 caracteres (~80 palavras) |
| Teto | 1.800 caracteres (~300 palavras), bloqueador no script |
| Gancho | até 100 caracteres |
| Linha | até ~120 caracteres, para não quebrar feio no mobile |

Contagem inclui espaços, quebras de linha, link e hashtags. O link sozinho come uns
200 caracteres, então o texto real do post fica em torno de 700 a 1.200.

O LinkedIn aceita 3.000 caracteres. O teto aqui é editorial, não técnico: post que
esgota o assunto entrega o conteúdo ali mesmo e mata o clique. Se o argumento não coube,
ele é do artigo.

---

## Voz

A mesma do blog. Valem integralmente `style-dna.md`, `manual-redacao.md` e
`anti-ia-rules.md`, com estes recortes que mais aparecem em post curto:

- **Zero em dash (—).** Vírgula, parênteses, dois pontos ou ponto final.
- **Zero frase-conclusão** ("Em resumo", "Por fim", "Em última análise", "Concluindo").
- **Zero abertura proibida** ("Imagine que", "Em um mundo cada vez mais", "Parece ficção científica").
- **Zero anáfora staccato.** Três frases curtas seguidas com a mesma estrutura reprova.
  Vale a exceção de uma frase-parágrafo de 4 a 8 palavras por post.
- **Zero emoji decorativo.** Post de página de empresa, não de perfil pessoal.
  Emoji só se for parte de um dado ou de uma marca, o que na prática significa nunca.
- **Sem "🚀", sem "👇", sem "Link nos comentários".** O link está no corpo.
- **Sem valor monetário** de preço ou piso de investimento, igual ao blog.
  Sustentar por redução percentual e ROI.
- **Negrito não existe no LinkedIn.** Não usar `**` nem caracteres Unicode falsos de negrito,
  que quebram leitor de tela e busca.

---

## Link e UTM (bloqueador)

O link do artigo sai sempre com a taxonomia de `utm-tracking.md`:

```
https://metakosmos.com.br/blog/[slug]?utm_source=linkedin-organico&utm_medium=organic-social&utm_campaign=[pilarN-tema]&utm_content=[slug]
```

- `utm_source` é sempre `linkedin-organico`.
- `utm_medium` é sempre `organic-social`.
- `utm_campaign` copia o campo do pilar já usado no artigo (ex: `pilar2-provador-virtual`).
- `utm_content` é o slug do artigo.

**Um link por post.** Dois links no corpo derrubam a entrega e dividem o clique.
Se o post precisar mandar para o `/estudo`, citar a página pelo nome, sem segunda URL.

**O artigo não precisa estar no ar para o post sair.** O script bate HTTP na URL e avisa
se ela responde 404, mas isso é aviso, não bloqueio: decisão do usuário é poder postar
antes, porque o artigo entra no ar em algum momento e o link passa a funcionar sozinho.

Na prática isso é a regra, não a exceção: o post é **publicado automaticamente no passo 10**,
quando o artigo ainda é rascunho no Payload. Ou seja, todo post nasce com o link em 404 e
ele se conserta sozinho quando o artigo sobe. Quanto mais cedo o artigo subir, menor a
janela em que alguém clica e não acha nada.

---

## Hashtags

3 a 5, sempre no fim, sempre sem acento. Base fixa mais uma ou duas do pilar:

- Base: `#ImmersiveCommerce` `#Phygital` `#Ecommerce`
- Pilar 1: `#AgenticCommerce` `#IAnoVarejo`
- Pilar 2: `#ProvadorVirtual` `#TryOn`
- Pilar 3: `#Visualizador3D` `#RealidadeAumentada`
- Pilar 5: `#PerformanceEcommerce` `#CRO`
- Pilar 6: `#Cases`

Não repetir hashtag que já esteja escrita no corpo como palavra.

---

## O que este formato custa (registrado, não é para debater a cada post)

O link acima da dobra é decisão do usuário. Ele entrega mais clique e menos alcance:
o LinkedIn distribui menos post com URL externa no corpo. As alternativas descartadas
foram link no primeiro comentário e post sem link. Se um dia a entrega cair a ponto de
incomodar, o ponto de mudança é este, e o resto do formato continua válido.

---

## Checklist antes de publicar (todos bloqueadores)

- [ ] Gancho com até 100 caracteres, sem hashtag e sem pergunta retórica
- [ ] Linha `Leia completo em:` imediatamente depois do gancho
- [ ] Exatamente 1 URL no post, com os 4 UTMs corretos
- [ ] Total entre 500 e 1.800 caracteres (alvo 900 a 1.400)
- [ ] 3 ou 4 blocos de corpo, no máximo
- [ ] Pelo menos 1 número, conferido na fonte
- [ ] O post **não responde** a pergunta que levantou
- [ ] Zero em dash
- [ ] Zero frase-conclusão e zero abertura proibida
- [ ] Zero emoji e zero markdown (`**`, `##`, `- `)
- [ ] 3 a 5 hashtags na última linha
- [ ] Sem valor monetário
