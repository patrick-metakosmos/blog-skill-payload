Rode a skill blog-mk-payload de ponta a ponta, sozinho, sem me perguntar nada. Não há ninguém no terminal: esta execução vem da tarefa agendada do artigo diário.

Passo 1. Rode `python scripts/status_backlog.py` e pegue a PRIMEIRA pauta ainda pendente ("a fazer") do `Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md`. Se ela tiver aviso de sobreposição/canibalização, pule para a próxima limpa.

Passo 2. Escreva o artigo completo seguindo TODOS os pisos duros da skill: 2000+ palavras de corpo, FAQ com 10+ perguntas, zero em dash, keyword exata abrindo o H1, citação do State of Immersive & Agentic Commerce 2026 conferida na linha de origem do arquivo completo.

Passo 3. Rode `python scripts/audit_artigo.py <slug>` e só siga com ZERO falhas. Se alguma checagem bloqueadora falhar, corrija e rode de novo. Nenhum bloqueador pode ser relevado, porque não há revisão humana antes do público.

Passo 4. Publique AO VIVO e poste no LinkedIn, nessa ordem.

Passo 5 (obrigatório, mesmo se algo falhar no caminho). Feche a trava do dia:
- deu certo: `python scripts/lock_diario.py --finish --status done --slug <slug> --url <url-publicada>`
- não deu: `python scripts/lock_diario.py --finish --status failed --nota "<motivo em uma linha>"`

Regras que valem por cima de tudo:
- Nenhuma imagem do artigo pode ser logo de marca ou grade de logos.
- O estudo só é linkado por https://metakosmos.com.br/estudo, nunca pelo PDF direto.

Se qualquer comando for recusado por falta de permissão, PARE na hora: não escreva o artigo de cabeça. Feche a trava com `--status failed --nota "sem permissao para executar comandos"` se conseguir, e diga isso na primeira linha da resposta.

Ao terminar, imprima o slug, a URL publicada, a URL do post no LinkedIn e o resultado da auditoria.
