Rode a skill blog-mk-payload de ponta a ponta, sozinho, sem me perguntar nada. Não há ninguém no terminal: esta execução vem da tarefa agendada do artigo diário.

Passo 1. Rode `python scripts/status_backlog.py` e pegue a PRIMEIRA pauta ainda pendente ("a fazer"; as marcadas "⏸️ pausada" ficam de fora) do `Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md`. Se ela tiver aviso de sobreposição/canibalização, pule para a próxima limpa.

Passo 2. Escreva o artigo completo seguindo TODOS os pisos duros da skill: 2000+ palavras de corpo, FAQ com 10+ perguntas, zero em dash, keyword exata abrindo o H1, citação do State of Immersive & Agentic Commerce 2026 conferida na linha de origem do arquivo completo.

Passo 3. Rode `python scripts/audit_artigo.py <slug>` e só siga com ZERO falhas. Se alguma checagem bloqueadora falhar, corrija e rode de novo. Nenhum bloqueador pode ser relevado, porque não há revisão humana antes do público.

Passo 4. Nesta ordem: publique o artigo AO VIVO e poste na página da metaKosmos no LinkedIn. A geração e a publicação diária no perfil pessoal do Ian Borges (CEO) estão PAUSADAS por pedido do usuário em 12/10/2026. Não gere linkedin-ceo.md nem execute o envio com --perfil ceo. Essa decisão prevalece sobre instruções anteriores da skill. Mantenha o cenário Make 4928134 desativado e o arquivo references/linkedin-ceo-pausado.md presente até novo pedido explícito de retomada.

A pausa do CEO é intencional e não é falha. Conclua o dia como done quando o artigo e o post da página saírem normalmente. Se algum fluxo antigo chamar o publicador do CEO, ele retorna código 3 sem enviar nada; registre "LinkedIn do CEO pausado por decisão do usuário" e siga.

Passo 5 (obrigatório, mesmo se algo falhar no caminho). Feche a trava do dia:
- deu certo: `python scripts/lock_diario.py --finish --status done --slug <slug> --url <url-publicada>`
- não deu: `python scripts/lock_diario.py --finish --status failed --nota "<motivo em uma linha>"`

Regras que valem por cima de tudo:
- Nenhuma imagem do artigo pode ser logo de marca ou grade de logos.
- O estudo só é linkado por https://metakosmos.com.br/estudo, nunca pelo PDF direto.

Se qualquer comando for recusado por falta de permissão, PARE na hora: não escreva o artigo de cabeça. Feche a trava com `--status failed --nota "sem permissao para executar comandos"` se conseguir, e diga isso na primeira linha da resposta.

Ao terminar, imprima o slug, a URL publicada, a URL do post no LinkedIn, "LinkedIn do CEO pausado por decisão do usuário" e o resultado da auditoria.
