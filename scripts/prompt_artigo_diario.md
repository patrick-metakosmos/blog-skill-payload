Rode a skill blog-mk-payload de ponta a ponta, sozinho, sem me perguntar nada. Não há ninguém no terminal: esta execução vem da tarefa agendada do artigo diário.

Passo 1. Rode `python scripts/status_backlog.py` e pegue a PRIMEIRA pauta ainda pendente ("a fazer") do `Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md`. Se ela tiver aviso de sobreposição/canibalização, pule para a próxima limpa.

Passo 2. Escreva o artigo completo seguindo TODOS os pisos duros da skill: 2000+ palavras de corpo, FAQ com 10+ perguntas, zero em dash, keyword exata abrindo o H1, citação do State of Immersive & Agentic Commerce 2026 conferida na linha de origem do arquivo completo.

Passo 3. Rode `python scripts/audit_artigo.py <slug>` e só siga com ZERO falhas. Se alguma checagem bloqueadora falhar, corrija e rode de novo. Nenhum bloqueador pode ser relevado, porque não há revisão humana antes do público.

Passo 4. Nesta ordem: publique o artigo AO VIVO, poste na página da metaKosmos no LinkedIn e, por último, o post pessoal do Ian Borges (CEO). Para o do Ian, escreva `output/<slug>/linkedin-ceo.md` seguindo `references/linkedin-ceo.md`, o guia completo `references/Tom de Voz — Ian Borges Guia para Automação LinkedIn.md` e o repertório `references/ian-repertorio.md` (convicções e histórias reais dele, tiradas de falas gravadas): é a opinião original dele sobre o assunto, nunca um resumo do artigo, e nenhum fato pessoal que não esteja no repertório ou no guia. Dispare com `python scripts/linkedin_publish.py <slug> --perfil ceo`. Se esse comando sair com código 3, o perfil do Ian ainda não está configurado no Make: isso NÃO é falha, siga em frente e registre no resumo.

O post do Ian é complementar. Se ele reprovar na validação, corrija o `linkedin-ceo.md` e rode de novo. Se ainda assim não sair, por qualquer motivo, NÃO marque o dia como failed: o artigo e o post da página já estão no ar, e failed faria a repescagem escrever um SEGUNDO artigo no mesmo dia. Feche como done e explique a falha do post do Ian no `--nota`.

Passo 5 (obrigatório, mesmo se algo falhar no caminho). Feche a trava do dia:
- deu certo: `python scripts/lock_diario.py --finish --status done --slug <slug> --url <url-publicada>`
- não deu: `python scripts/lock_diario.py --finish --status failed --nota "<motivo em uma linha>"`

Regras que valem por cima de tudo:
- Nenhuma imagem do artigo pode ser logo de marca ou grade de logos.
- O estudo só é linkado por https://metakosmos.com.br/estudo, nunca pelo PDF direto.

Se qualquer comando for recusado por falta de permissão, PARE na hora: não escreva o artigo de cabeça. Feche a trava com `--status failed --nota "sem permissao para executar comandos"` se conseguir, e diga isso na primeira linha da resposta.

Ao terminar, imprima o slug, a URL publicada, a URL do post no LinkedIn, o resultado do post do Ian (postado, ou "perfil do CEO não configurado") e o resultado da auditoria.
