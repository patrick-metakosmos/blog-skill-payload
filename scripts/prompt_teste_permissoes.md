Teste de fumaça do trigger diário. NÃO escreva artigo, NÃO publique, NÃO poste, NÃO commite, NÃO rode lock_diario.py com --acquire nem --finish.

Faça só estes três passos, que provam que a sessão tem as permissões que o artigo diário precisa:

1. Execute `python scripts/lock_diario.py --show` e guarde a saída (prova permissão de rodar comandos).
2. Grave o arquivo `logs/teste-permissoes.txt` contendo a data e hora atuais e a saída do passo 1 (prova permissão de gravar arquivos).
3. Execute `python scripts/status_backlog.py --dry-run` e identifique a próxima pauta pendente.

Responda com exatamente estas linhas:
PERMISSAO-COMANDO: OK ou FALHOU
PERMISSAO-ARQUIVO: OK ou FALHOU
PROXIMA-PAUTA: <número e título>

Se algum passo for recusado por falta de permissão, marque FALHOU e não tente contornar.
