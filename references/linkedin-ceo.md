# Post de LinkedIn - perfil pessoal do Ian Borges (CEO)

Segundo post automático do fim do fluxo. Sai **depois** do post da página da metaKosmos,
no perfil pessoal do Ian, em primeira pessoa.

**A voz vem inteira de `Tom de Voz — Ian Borges Guia para Automação LinkedIn.md`.**
Carregue o guia completo antes de escrever (é curto, cerca de 16 KB). Este arquivo aqui
só traduz o guia em formato de arquivo, regras que o script cobra e fluxo de publicação.
Quando os dois divergirem sobre voz, vale o guia.

---

## A regra que mais importa

O artigo é só o **gatilho temático**. O post é o **take do Ian** sobre aquele assunto: a
leitura de mercado dele, a visão de futuro, o dado que valida, o convite. Nunca um resumo
nem uma reescrita do artigo, e nunca o mesmo texto da página com "eu" no lugar de "a mK".

Se o assunto do artigo não der um take honesto, diga isso em vez de inventar contexto.

---

## Opinião, não relatório (o erro mais comum)

O jeito mais fácil de errar este post é escrever um relatório com voz animada: pergunta no
gancho, quatro números do estudo em sequência, uma analogia e o CTA. Fica correto e
impessoal. **Teste:** troque "Ian" por "metaKosmos". Se o texto continuar funcionando, ele
está institucional.

O post precisa de **uma posição**, uma frase que alguém poderia contestar. "AR aumenta
conversão" não é posição, é dado. "Foto de produto está virando o catálogo de papel do
varejo online" é posição, é aposta.

Estrutura que funciona:

1. **A posição no gancho ou na linha 2.** Pode vir anunciada: "Vou falar uma coisa que
   talvez incomode:", "Minha aposta:", "Vou ser direto contigo:".
2. **Por que ele pensa isso:** a leitura de mercado dele, com **1 ou 2 dados** que sustentam
   o argumento. O dado serve à opinião, não é o protagonista.
3. **O que está em jogo:** a curva de adoção, o "mercado dormindo", quem vai ficar para trás.
4. **Fechamento que convida a discordar:** pergunta direta, "me diz sem filtro", provocação.

**Pessoa gramatical:** opinião na **primeira do singular** ("eu acho", "minha aposta", "me
incomoda", "confesso"); realização na **primeira do plural** ("a gente construiu", "nosso
estudo"). É assim que a voz pessoal convive com o framing coletivo que o guia pede.

**De onde vem a opinião: `ian-repertorio.md`.** São as convicções, histórias e o jeito de
argumentar que ele mostra em falas públicas gravadas. Carregue sempre. A posição do post
deve sair de uma convicção de lá (seção 1), e a âncora pessoal, de uma história de lá
(seção 2). Respeite as seções 5 e 6 do repertório: o que não passa do palco para o
LinkedIn e os números que ainda não estão liberados.

**Nunca inventar bastidor.** Opinião e sentimento podem ser escritos; fato, não. Nada de
reunião, cliente, conversa, viagem ou número que não esteja na seção 10 do guia ou no
artigo-gatilho. Âncoras pessoais **verdadeiras** que já estão no guia: ele apresentou o estudo
no Fórum E-commerce Brasil 2026 (Plenária Pulsar), a visão de ser referência mundial em
Immersive Commerce, o "From Good to Woow".

Avisos do script que apontam para esse erro: **mais de 3 percentuais** no corpo ("virou
relatório") e **nenhuma marca de primeira pessoa do singular** ("sem voz pessoal").

---

## Página x perfil do Ian (não misturar as regras)

| Regra | Página (`linkedin.md`) | Perfil do Ian (`linkedin-ceo.md`) |
|---|---|---|
| Voz | institucional mK, 3ª pessoa | Ian, 1ª pessoa, framing coletivo ("a gente") |
| Gancho | afirmação ou dado, **nunca** pergunta | dado, pergunta retórica **ou** afirmação contraintuitiva |
| Link | linha 3, no corpo | **no corpo**, em qualquer posição (padrão), ver abaixo |
| Tamanho | 500 a 1.800, alvo 900 a 1.400 | **800 a 1.800**, ideal 1.200 a 1.500 |
| Emoji | proibido | só emoticon de caractere, tipo `;)` e `:)`, com moderação |
| Hashtags | 3 a 5 obrigatórias | 0 a 5, só na última linha, só se couberem |
| Fechamento | CTA raro (o link é o CTA) | CTA, provocação ou pergunta que gere comentário |
| Valor em R$ | bloqueado | tamanho de mercado pode (seção 10 do guia); preço e investimento nunca |

---

## Arquivo de saída

```
output/[slug]/
├── linkedin.md       ← página
└── linkedin-ceo.md   ← este
```

Formato (o script lê o corpo depois do primeiro `---` isolado):

```markdown
# LinkedIn (perfil Ian Borges) - [slug]

**Perfil:** Ian Borges (CEO)
**Artigo:** https://metakosmos.com.br/blog/[slug]
**Link:** https://metakosmos.com.br/blog/[slug]?utm_source=linkedin-organico&utm_medium=organic-social&utm_campaign=[pilarN-tema]&utm_content=ian-[slug]
**Registro:** Educacional | Vendas | Networking | Social   (seção 8 do guia)
**Ângulo:** Visionário/Urgência | Transparência/Bastidor | Dados/Autoridade   (seção 12)

---
[texto do post, exatamente como vai para o LinkedIn]
```

O campo **Link** é a URL com UTM que o post deve usar. No modo padrão (`corpo`) ela aparece
no próprio texto; no cabeçalho, serve de referência para quem revisar.

---

## Link: onde ele vai (`LINKEDIN_CEO_LINK` no `.env`)

| Modo | O que faz | Quando usar |
|---|---|---|
| `corpo` (padrão) | exatamente 1 URL no corpo, com UTM; o LinkedIn mostra o preview com a imagem do artigo | todo dia, automático |
| `nenhum` | sem URL em lugar nenhum | post de pura opinião; o link já está na página |
| `comentario` | corpo sem URL; o link vai num comentário **feito à mão**, logado como o Ian | só se alguém comentar todo dia; não é automático |

**Por que não comentário automático, apesar de o guia preferir:** testado em 18/09/2026. O
post sai, mas comentar em perfil pessoal pela API exige acesso de parceiro do LinkedIn
(Community Management API), que o app do Make não tem: `403 partnerApiSocialActions.CREATE`.
O post do teste foi ao ar dizendo "link nos comentários" sem link nenhum, até alguém
comentar à mão. Por isso o padrão é `corpo`, e o script **bloqueia** post que fala em
"link nos comentários" nesse modo. O custo, registrado: link no corpo reduz um pouco o
alcance orgânico, em troca de preview com imagem e clique rastreável.

O padrão mora no código (`linkedin_publish.py`), não no `.env`, para as duas máquinas se
comportarem igual. `LINKEDIN_CEO_LINK` no `.env` só existe para exceção.

**UTM:** mesma taxonomia de `utm-tracking.md`, com `utm_content=ian-[slug]`. O prefixo
`ian-` é o que separa, no GA4, o clique que veio do perfil do Ian do clique que veio da
página (`utm_content=[slug]`). Sem ele, os dois se misturam.

---

## O que o script cobra (`linkedin_publish.py --perfil ceo`)

**Bloqueadores:** tamanho fora de 800 a 1.800 · gancho vazio ou começando com hashtag ·
quantidade de URL diferente de 1 no modo `corpo` (padrão) · "link nos comentários" no
modo `corpo` · URL no corpo no modo `comentario` · link sem os UTMs certos · `utm_content` sem o prefixo `ian-` · em dash · frase de
conclusão ("em resumo", "por fim"...) · palavrão · "obrigada" (na voz do Ian é
"obrigado") · tempo relativo que envelhece ("essa semana", "semana passada", "mês
passado") · `**` de markdown · emoji gráfico · nenhum número no corpo · hashtag fora da
última linha · mais de 5 hashtags · hashtag com acento.

**Avisos:** tamanho fora do ideal de 1.200 a 1.500 · gancho acima de 140 caracteres (o
"ver mais" corta antes no celular) · corpo sem avisar do link nos comentários · valor em
R$ (confira se é tamanho de mercado, não preço) · "ontem"/"hoje cedo" · vocabulário de IA ·
fechamento sem pergunta.

O que o script **não** consegue checar, e é seu trabalho, pelo checklist da seção 13 do
guia: se é take original e não resumo, se soa como o Ian e não como IA, se o dado citado
está na seção 10 do guia ou no próprio artigo. **Nunca inventar dado.**

---

## Fluxo

Passo 10 da `SKILL.md`, **depois** do post da página:

```bash
python scripts/linkedin_publish.py <slug> --perfil ceo --dry-run   # valida e mostra
python scripts/linkedin_publish.py <slug> --perfil ceo             # POSTA no perfil do Ian
```

Códigos de saída:

- `0` postado (ou validação ok em `--check` / `--dry-run`)
- `1` erro: validação reprovou, trava de duplicidade, webhook falhou
- `3` **perfil do CEO ainda não configurado** (`LINKEDIN_CEO_WEBHOOK_URL` vazio). **Não é
  falha.** O fluxo segue normalmente, e o post do Ian só passa a sair quando o cenário
  dele existir no Make.

Trava: o primeiro disparo bem-sucedido grava `output/[slug]/.linkedin-ceo-posted.json`,
separado do marcador da página. Um destino nunca bloqueia nem libera o outro.

---

## Make (cenário próprio, separado do da página)

| Item | Valor |
|---|---|
| Cenário | `[mK] Blog -> LinkedIn (perfil Ian Borges)`, ID **4928134** |
| Webhook | ID 2824923 (o primeiro, 2824796, foi apagado com um post preso na fila). A URL vive em `LINKEDIN_CEO_WEBHOOK_URL` no `.env`, **nunca aqui** (quem tem a URL posta no perfil do CEO) |
| Módulo 2 | `linkedin:CreatePost` v2 ("Create a User Text Post"), `content={{1.content}}`, `visibility=PUBLIC` |
| Conexão | `Ian's LinkedIn connection` (ID 4867969, tipo `linkedin2`, conta "Ian Borges"), permissões `w_member_social` e `r_liteprofile`, válida até 09/2027 |

Separado de propósito: se a conexão do Ian expirar ou for revogada, só o post dele para.
O da página, que usa outra conexão, continua saindo.

**Cenário desligado é perigo.** Webhook de cenário inativo enfileira as chamadas e, quando o
cenário volta, publica tudo o que ficou na fila; e o script grava a trava achando que
postou. Se o cenário cair, tire `LINKEDIN_CEO_WEBHOOK_URL` do `.env` até religar: sem a URL,
o script sai com código 3 e não envia nada.

Já aconteceu: no primeiro post, o erro do comentário deixou o post na fila do webhook. Religar
o cenário teria publicado de novo. A saída foi criar um webhook novo, apontar o cenário e o
`.env` para ele e apagar o antigo com a fila junto. Pelo mesmo motivo, **nunca clique em
"Replay"** na execução com erro de 18/09/2026: ela republica o post.

**Primeiro post:** 18/09/2026, artigo `como-visualizar-produto-em-casa-antes-de-comprar`.
