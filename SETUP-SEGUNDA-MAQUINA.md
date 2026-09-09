# Instalar o artigo diário numa segunda máquina

O trigger diário roda em quantas máquinas você quiser. Só sai **um artigo por dia**,
não importa quantas estejam ligadas: antes de escrever qualquer coisa, cada máquina
tenta cravar o lock do dia no GitHub, e só quem consegue o `git push` segue adiante.

## Como a trava funciona

1. A máquina roda `lock_diario.py --acquire`.
2. Ele lê `locks/<AAAA-MM-DD>.json` no GitHub. Se já existe com status `done`, ou
   `running` de menos de 3 horas, **sai sem fazer nada**.
3. Confere no Payload se já existe post criado hoje. Se existe, sai. Isso cobre o caso
   de alguém ter escrito o artigo do dia à mão, fora do pipeline.
4. Cria o lock e tenta `git push`. O push é atômico no servidor: se as duas máquinas
   tentarem no mesmo segundo, **uma leva rejeição e desiste**.
5. Quem ganhou escreve o artigo, publica e fecha o lock com `--finish --status done`.

Se a máquina que pegou o lock travar no meio, o lock fica `running`. Depois de 3 horas
(`--stale-hours`), a outra máquina assume. Por isso vale registrar um horário de
repescagem além do horário principal.

Perder a corrida **nunca** mexe no trabalho local: o script desfaz só o próprio commit
e só o arquivo de lock, e todo `pull --rebase` usa autostash.

## Passo a passo na máquina nova

**1. Programas** (se já tiver, pule)

- [Git para Windows](https://git-scm.com/download/win)
- [Node.js LTS](https://nodejs.org) — o CLI do Claude Code depende dele
- [Python 3.11+](https://python.org) — marque "Add python.exe to PATH" no instalador

**2. CLI do Claude Code**

```powershell
npm install -g @anthropic-ai/claude-code
claude          # abra uma vez e faça login. O trigger usa esta sessão.
```

**3. Acesso ao repositório**

O repo é privado. Adicione a conta GitHub dela como colaboradora em
`github.com/patrick-metakosmos/blog-skill-payload` → Settings → Collaborators.

```powershell
cd $HOME\Desktop
git clone https://github.com/patrick-metakosmos/blog-skill-payload.git "blog mK Payload"
```

**4. Credenciais (`.env`)**

O `.env` **não** está no repo, de propósito. Copie o arquivo por um canal seguro
(1Password, Bitwarden, cofre do Zoho — nunca WhatsApp ou e-mail) para a raiz da pasta
clonada.

> Melhor ainda: crie um usuário próprio dela no painel do Payload e monte um `.env` com
> o login dela. Assim dá para saber quem publicou o quê, e revogar o acesso sem trocar
> a sua senha.

**5. Registrar a tarefa**

Escalone o horário em relação à sua máquina. Sugestão: você às 07:00 (com repescagem
às 11:00) e ela às 07:30 (com repescagem às 14:00).

```powershell
cd "$HOME\Desktop\blog mK Payload"
powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Hora "07:30,14:00"
```

**6. Conferir**

```powershell
python scripts\lock_diario.py --show        # mostra o lock de hoje
Get-ScheduledTask -TaskName "Blog mK - artigo diario"
```

Para um teste de verdade (gera e publica um artigo ao vivo):

```powershell
Start-ScheduledTask -TaskName "Blog mK - artigo diario"
Get-Content logs\artigo-diario-*.log -Wait -Tail 30
```

## Comandos do dia a dia

```powershell
python scripts\lock_diario.py --show                  # quem fez o artigo de hoje?
python scripts\lock_diario.py --show --dia 2026-09-08 # e o de ontem?
python scripts\lock_diario.py --acquire --force       # forçar um 2o artigo no mesmo dia
powershell -File scripts\registrar_tarefa_diaria.ps1 -Hora "06:30"   # mudar horário
powershell -File scripts\registrar_tarefa_diaria.ps1 -Remover        # desligar
```

O histórico fica em `locks/` no próprio repo: um JSON por dia, com máquina, horário,
slug e URL publicada.

## O que ainda depende de cada máquina

- **A sessão do Claude Code precisa estar logada.** Se a autenticação expirar, a tarefa
  falha e o log registra; o lock é marcado `failed` e a outra máquina assume no horário dela.
- **A tarefa roda com o usuário logado.** PC desligado às 7h roda quando ligar
  (`StartWhenAvailable`), mas se ficar desligado o dia todo, a outra máquina cobre.
- **Publica ao vivo, sem revisão humana.** A auditoria bloqueadora do passo 8.5 é a única
  rede antes do público. Nenhum bloqueador pode ser relevado.
