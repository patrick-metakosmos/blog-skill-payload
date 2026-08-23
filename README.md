# blog-mk-payload

Skill do Claude Code para gerar, reescrever, humanizar, auditar e publicar artigos do blog
metaKosmos no Payload CMS. Fluxo completo, guardrails editoriais e scripts de publicação
vivem nesta pasta.

## Instalação (cada pessoa)

1. Clone este repositório em qualquer pasta local:
   ```
   git clone https://github.com/patrick-metakosmos/blog-skill-payload.git "blog mK Payload"
   ```
2. Copie `.env.example` para `.env` e preencha com o **seu próprio** login do Payload
   (nunca reutilize a senha de outra pessoa, e nunca commite o `.env`).
3. Crie o arquivo ponteiro da skill em `~/.claude/skills/blog-mk-payload/SKILL.md` com o
   conteúdo abaixo, ajustando o `BASE` para o caminho onde você clonou este repositório:

   ```markdown
   ---
   name: blog-mk-payload
   description: Gera, reescreve, humaniza, audita e publica artigos do blog metaKosmos no Payload CMS (Lexical).
   ---

   # Blog mK (Payload)

   Esta skill é um ponteiro. A implementação real vive em uma única pasta de origem.

   **BASE:** `<caminho onde você clonou este repositório>`

   Leia o arquivo completo `BASE\SKILL.md` e siga-o à risca.
   ```

4. `pip install -r requirements.txt` se houver dependências dos scripts (ver `scripts/`).

## Atualizar

Como o clone É a pasta base, `git pull` já atualiza scripts, referências e o backlog
editorial para todo mundo. Ao terminar um artigo, marque a linha correspondente no
`Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md` e dê `git add` + `git commit` + `git push`
para compartilhar o progresso com o time.

## O que não está versionado

- `.env` — credenciais pessoais do Payload (use `.env.example` como modelo)
- `backups/` — dumps de recuperação locais
- `output/` — rascunhos e revisões em andamento
- `*.zip` — handoffs antigos, substituídos por este repositório
