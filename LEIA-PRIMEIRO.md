# LEIA PRIMEIRO — Skill de Blog mK (Payload)

Bem-vinda! Esta pasta é uma "skill" que faz o Claude escrever e publicar artigos do blog da metaKosmos no padrão da casa (voz, GEO/AEO, anti-IA) e subir como rascunho no site.

Você quase não precisa mexer em nada técnico: o **próprio Claude faz o setup pra você**. Siga os 4 passos.

---

## Passo 1 — Descompacte a pasta

Extraia o `.zip` que você recebeu para um lugar fácil, por exemplo a **Área de Trabalho**. Você vai ter uma pasta chamada `blog mK Payload`.

## Passo 2 — Tenha o Python instalado (uma vez só)

O publicador usa Python (não precisa instalar mais nada além dele).
- Para testar se já tem: o Claude vai checar pra você no passo 3.
- Se não tiver, baixe em https://www.python.org/downloads/ e instale (no Windows, marque a opção "Add Python to PATH").

## Passo 3 — Abra o Claude nesta pasta e peça o setup

No Claude (mesmo app que a gente usa), com acesso a esta pasta, escreva:

> **"Leia o arquivo INSTRUCOES-PARA-O-CLAUDE.md e execute o setup desta skill pra mim."**

O Claude vai, sozinho (pedindo sua aprovação nos comandos):
1. Conferir o Python.
2. Criar o arquivo de credenciais (`.env`).
3. Testar o login no painel.
4. Atualizar o catálogo de imagens.

Ele vai te pedir **duas coisas**: o **e-mail** e a **senha** do seu login no painel Payload (metakosmos.com.br/admin). Se preferir não colar a senha no chat, o Claude te mostra como digitá-la você mesma no arquivo `.env`.

> Dica de segurança: use o **seu próprio login** do painel Payload. Assim os rascunhos ficam registrados no seu nome.

## Passo 4 — Peça artigos

Pronto! A partir daí é só conversar com o Claude. Exemplos:

- *"Faz uma **pauta** para a keyword 'provador virtual de óculos', pilar 2, funil MOFU."*
- *"**Gera** um artigo sobre ROI do provador virtual."*
- *"**Audita** este texto e me dá o score."* (colando um texto)
- *"**Publica** o artigo roi-provador-virtual."* → ele sobe como **rascunho**, você revisa no painel antes de publicar de verdade.

---

## Coisas importantes

- **Nada vai ao ar sozinho.** A publicação sempre cria um **rascunho**. Você revisa no painel (metakosmos.com.br/admin) e publica manualmente.
- **Tem uma versão antiga (WordPress) da skill** com nome parecido no Claude. Sempre peça pro Claude "seguir o `SKILL.md` desta pasta" pra ele usar a versão certa (Payload).
- **Dúvidas do que cada arquivo faz?** Veja o `HANDOFF.md` (explicação detalhada) ou o `INSTRUCOES-PARA-O-CLAUDE.md` (o passo a passo que o Claude executa).

Qualquer coisa, peça ajuda ao próprio Claude: ele conhece esta skill lendo o `SKILL.md`.
