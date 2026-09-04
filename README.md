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
3. Copie o arquivo **`ponteiro-skill.md`** deste repositório para
   `~/.claude/skills/blog-mk-payload/SKILL.md` e troque só a linha `**BASE:**` pelo caminho
   onde você clonou o repositório.

   Não escreva o ponteiro à mão. Ele carrega as correções de rota e as regras do usuário,
   que mudam com o tempo, e uma versão resumida faz a skill trabalhar com regra velha.
   Ao dar `git pull`, confira se o `ponteiro-skill.md` mudou e recopie quando mudar.

4. Os scripts usam só biblioteca padrão do Python 3. Não há `requirements.txt`.

## Atualizar

**Ver [`ATUALIZAR.md`](ATUALIZAR.md)** — tem um bloco pronto para colar no Claude Code,
que cuida do pull, do ponteiro e do `.env` de uma vez.


Como o clone É a pasta base, `git pull` já atualiza scripts, referências e o backlog
editorial para todo mundo. Ao terminar um artigo, marque a linha correspondente no
`Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md` e dê `git add` + `git commit` + `git push`
para compartilhar o progresso com o time.

## Publicação: o que sai ao vivo automaticamente

Desde 02/09/2026, ao terminar um artigo a skill publica **ao vivo**, nesta ordem:

```bash
python scripts/payload_publish.py <slug> --status published   # artigo AO VIVO no blog
python scripts/linkedin_publish.py <slug>                     # post AO VIVO na página da mK
python scripts/status_backlog.py && python scripts/sync_payload_lists.py
```

Duas coisas que essa escolha implica, e que valem para quem for rodar:

- **Não existe mais revisão humana antes do público.** A auditoria do passo 8.5
  (`audit_artigo.py`) é a única rede de proteção. Nenhum bloqueador dela pode ser relevado.
- **A ordem importa.** O artigo sobe primeiro para o link do LinkedIn nascer funcionando.
  Invertida, todo post nasce apontando para 404.

O LinkedIn não deduplica: o primeiro disparo bem-sucedido grava
`output/<slug>/.linkedin-posted.json` e a trava recusa os próximos. `--force` só para
repost intencional. O post vai para a página da metaKosmos via webhook do Make
(cenário `[mK] Blog -> LinkedIn`), que precisa da conexão LinkedIn ativa e da variável
`LINKEDIN_WEBHOOK_URL` no `.env`.

## O que não está versionado

- `.env` — credenciais pessoais do Payload e `LINKEDIN_WEBHOOK_URL` (use `.env.example` como modelo)
- `backups/` — dumps de recuperação locais
- `output/` — rascunhos e revisões em andamento
- `*.zip` — handoffs antigos, substituídos por este repositório
