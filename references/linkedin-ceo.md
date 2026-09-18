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

## Página x perfil do Ian (não misturar as regras)

| Regra | Página (`linkedin.md`) | Perfil do Ian (`linkedin-ceo.md`) |
|---|---|---|
| Voz | institucional mK, 3ª pessoa | Ian, 1ª pessoa, framing coletivo ("a gente") |
| Gancho | afirmação ou dado, **nunca** pergunta | dado, pergunta retórica **ou** afirmação contraintuitiva |
| Link | linha 3, no corpo | **no primeiro comentário** (padrão), ver abaixo |
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

O campo **Link** é o que vai no comentário. Ele fica no cabeçalho, e não no corpo, porque
no modo padrão o corpo não leva URL nenhuma.

---

## Link: onde ele vai (`LINKEDIN_CEO_LINK` no `.env`)

| Modo | O que faz | Quando usar |
|---|---|---|
| `comentario` (padrão) | corpo sem URL; o cenário publica o post e depois comenta o `**Link:**` | o que o guia recomenda: sem penalidade de alcance |
| `corpo` | exatamente 1 URL no corpo, com UTM | quando o preview com thumbnail valer mais que o alcance |
| `nenhum` | sem URL em lugar nenhum | post de pura opinião; o link já está na página |

No modo `comentario`, o corpo precisa avisar o leitor ("link nos comentários"), senão
ninguém procura. O script avisa se faltar.

**UTM:** mesma taxonomia de `utm-tracking.md`, com `utm_content=ian-[slug]`. O prefixo
`ian-` é o que separa, no GA4, o clique que veio do perfil do Ian do clique que veio da
página (`utm_content=[slug]`). Sem ele, os dois se misturam.

---

## O que o script cobra (`linkedin_publish.py --perfil ceo`)

**Bloqueadores:** tamanho fora de 800 a 1.800 · gancho vazio ou começando com hashtag ·
URL no corpo no modo `comentario` (ou quantidade errada no modo `corpo`) · `**Link:**`
faltando ou sem os UTMs certos · `utm_content` sem o prefixo `ian-` · em dash · frase de
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

`Webhook → LinkedIn v2 › Create a User Text Post (CreatePost) → [comentário com o link]`

Separado de propósito: se a conexão do Ian expirar ou for revogada, só o post dele para.
O da página, que usa outra conexão, continua saindo.

**Pré-requisito que só o Ian pode cumprir:** autorizar no Make uma conexão LinkedIn
**logado na conta dele**, com a permissão `w_member_social` (publicar como membro). A
conexão que já existe (`[MKL] metaKosmos (Patrick)`) não tem essa permissão e é de outra
pessoa: não serve e não deve ser reaproveitada.
