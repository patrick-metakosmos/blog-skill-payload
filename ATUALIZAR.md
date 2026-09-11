# Atualizar esta skill na sua máquina

O `git pull` sozinho não basta: o arquivo ponteiro vive fora do repositório
(em `~/.claude/skills/`) e o `.env` não é versionado.

**Cole o bloco abaixo no seu Claude Code**, na pasta do projeto, e siga o que ele pedir.

---

```
Preciso atualizar a skill blog-mk-payload nesta máquina. O git pull sozinho não
resolve, porque o arquivo ponteiro vive fora do repositório, o .env não é
versionado e a tarefa agendada é registrada localmente.

CONTEXTO DO QUE MUDOU EM 09/09/2026 (para você entender o que está instalando):

1. Duas regras editoriais novas, ambas BLOQUEADORAS:
   - Nenhuma imagem do artigo (capa ou corpo) pode ser logo de marca, grade de
     logos de clientes ou lockup institucional. Para citar marca cliente, usar a
     imagem do case dela e linkar o nome para /mkases/<slug>/.
   - O estudo State of Immersive & Agentic Commerce 2026 só pode ser linkado por
     https://metakosmos.com.br/estudo, que é a página que captura o lead. O link
     do PDF direto (/api/media/file/State%20of%20Immersive...) está proibido em
     artigo, LinkedIn e e-mail, porque entrega o ativo sem capturar nada.
   As duas viraram checagem programática no audit_artigo.py, e os 61 posts que já
   estavam no ar foram corrigidos.

2. Existe um trigger diário: uma tarefa do Windows que roda a skill de ponta a
   ponta de manhã, pega a próxima pauta pendente do backlog, escreve, audita,
   publica ao vivo e posta no LinkedIn. Ele roda na máquina do Patrick e vai
   rodar também na sua.

3. Como as duas máquinas rodam o mesmo trigger, existe uma trava: antes de
   escrever qualquer coisa, cada máquina tenta cravar locks/<data>.json no
   GitHub. Só quem consegue o git push segue; a outra sai sem fazer nada. Sai um
   artigo por dia, não importa quantas máquinas estejam ligadas.

4. Ao terminar um artigo, o backlog agora é commitado automaticamente
   (commit_listas.py). O BACKLOG-EDITORIAL.md no GitHub virou a fila
   compartilhada entre as máquinas.

FAÇA NESTA ORDEM:

1. Localize a pasta onde o repositório blog-skill-payload está clonado nesta
   máquina (o remote é github.com/patrick-metakosmos/blog-skill-payload).
   Se não achar, me pergunte o caminho.

2. Antes de puxar, verifique se há trabalho local não commitado com git status.
   Se houver, me mostre o que é e pergunte o que fazer. Não descarte nada.

3. git pull. Se der conflito, me mostre antes de resolver.

4. Copie o arquivo ponteiro-skill.md do repositório para
   ~/.claude/skills/blog-mk-payload/SKILL.md, trocando SOMENTE a linha que
   começa com "**BASE:**" pelo caminho real onde o repositório está clonado
   nesta máquina. Não reescreva nem resuma o resto do arquivo: ele carrega as
   correções de rota e as regras de publicação, e uma versão encurtada faz a
   skill trabalhar com regra velha. Este passo é obrigatório mesmo que o pull
   não tenha trazido conflito: as três regras novas do usuário estão nesse
   arquivo.

5. Confira se o .env existe na raiz do repositório e tem PAYLOAD_API_URL,
   PAYLOAD_EMAIL, PAYLOAD_PASSWORD e LINKEDIN_WEBHOOK_URL. Se faltar alguma,
   me avise para eu pedir ao Patrick. Nunca escreva esses valores em arquivo
   versionado e confirme que .env está no .gitignore.

6. Verifique se o CLI do Claude Code está instalado nesta máquina (comando
   `claude --version`). O trigger diário depende dele, e ter a extensão do
   VSCode não é suficiente. Se não estiver, instale com
   `npm install -g @anthropic-ai/claude-code` (precisa de Node.js) e me avise
   que preciso rodar `claude` uma vez para fazer login.

7. Registre a tarefa agendada, a partir da pasta do repositório:
     powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Hora "07:30,14:00"
   O 07:30 é o horário principal e o 14:00 é repescagem, para o caso de a outra
   máquina ter pegado a trava e travado no meio. Me mostre a saída do comando.

8. VERIFIQUE sem publicar nada. Rode só estes, que são leitura:
     PYTHONIOENCODING=utf-8 python scripts/lock_diario.py --show
     PYTHONIOENCODING=utf-8 python scripts/commit_listas.py --dry-run
     PYTHONIOENCODING=utf-8 python scripts/fix_blog_rules.py --check
   O primeiro mostra quem fez o artigo de hoje, o segundo mostra se o backlog
   local está desatualizado, o terceiro confirma zero violações das duas regras
   novas nos posts publicados.

   Depois rode o teste de fumaça do trigger, que usa a MESMA chamada do CLI da
   produção mas com um prompt que só prova as permissões (não pega a trava, não
   publica, não posta):
     scripts\artigo_diario.cmd teste
   e me mostre o arquivo logs\teste-permissoes-<data-de-hoje>.log. Precisa ter
   "PERMISSAO-COMANDO: OK" e "PERMISSAO-ARQUIVO: OK". Se vier FALHOU, a tarefa
   diária desta máquina vai falhar também: pare e me avise.

   NÃO rode nenhum destes durante a instalação, porque publicam ao vivo e são
   irreversíveis: Start-ScheduledTask, scripts\artigo_diario.cmd SEM o argumento
   "teste", payload_publish.py sem --dry-run, linkedin_publish.py.

9. Leia SETUP-SEGUNDA-MAQUINA.md e o SKILL.md do repositório e me faça um resumo
   curto do que muda na minha rotina, destacando:
   - as duas regras novas de imagem e de link do estudo
   - que ao terminar um artigo eu preciso rodar
     `python scripts/commit_listas.py --slug <slug>`, senão a outra máquina
     reescreve a mesma pauta
   - como saber se o artigo do dia já foi feito antes de começar a escrever
```

---

## Se você preferir fazer na mão

1. `git pull`
2. Copiar `ponteiro-skill.md` para `~/.claude/skills/blog-mk-payload/SKILL.md`,
   trocando só a linha `**BASE:**` pelo caminho do seu clone.
3. Conferir o `.env` (pedir ao Patrick o que faltar).
4. `npm install -g @anthropic-ai/claude-code` e rodar `claude` uma vez para logar.
5. `powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Hora "07:30,14:00"`
6. Conferir: `python scripts\lock_diario.py --show`

## Depois de todo `git pull`

Confira se o `ponteiro-skill.md` mudou. Se mudou, recopie para
`~/.claude/skills/blog-mk-payload/SKILL.md`. É o arquivo que carrega as regras
de publicação, e uma cópia velha faz a skill trabalhar com regra antiga.
