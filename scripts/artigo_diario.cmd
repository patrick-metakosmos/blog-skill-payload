@echo off
REM ============================================================
REM artigo_diario.cmd - dispara 1 artigo do blog mK por dia.
REM Roda nas DUAS maquinas (Patrick e estagiaria) sem duplicar:
REM lock_diario.py --acquire crava o lock do dia via push no GitHub,
REM e quem perde a corrida sai sem fazer nada.
REM Chamado pela tarefa agendada "Blog mK - artigo diario".
REM Registrar/alterar: scripts\registrar_tarefa_diaria.ps1
REM Log: logs\artigo-diario-AAAA-MM-DD.log
REM ============================================================
setlocal
REM UTF-8 no console, senao os acentos saem ilegiveis no log
chcp 65001 > nul
set "BASE=%~dp0.."
cd /d "%BASE%"
set "PYTHONIOENCODING=utf-8"

if not exist "logs" mkdir "logs"
for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "HOJE=%%a"
set "LOG=%BASE%\logs\artigo-diario-%HOJE%.log"

echo ============================================================>> "%LOG%"
echo INICIO %DATE% %TIME% em %COMPUTERNAME%>> "%LOG%"
echo ============================================================>> "%LOG%"

REM --- TRAVA: so uma maquina por dia passa daqui ---
python "%BASE%\scripts\lock_diario.py" --acquire >> "%LOG%" 2>&1
if errorlevel 1 (
    echo SAINDO: artigo de hoje ja foi feito ou outra maquina esta rodando.>> "%LOG%"
    endlocal & exit /b 0
)

call "%APPDATA%\npm\claude.cmd" -p ^
 "Rode a skill blog-mk-payload de ponta a ponta, sozinho, sem me perguntar nada. Passo 1: rode 'python scripts/status_backlog.py' e pegue a PRIMEIRA pauta ainda pendente (a fazer) do 'Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md' - se a primeira tiver aviso de sobreposicao/canibalizacao, pule para a proxima limpa. Passo 2: escreva o artigo completo seguindo TODOS os pisos duros da skill (2000+ palavras de corpo, FAQ 10+, zero em dash, keyword exata abrindo o H1, citacao do State of Immersive & Agentic Commerce 2026 conferida na origem). Passo 3: rode 'python scripts/audit_artigo.py <slug>' e so siga com ZERO falhas - se alguma checagem bloqueadora falhar, corrija e re-rode; nenhum bloqueador pode ser relevado, porque nao ha revisao humana antes do publico. Passo 4: publique AO VIVO e poste no LinkedIn, nessa ordem. Passo 5 (obrigatorio, mesmo se algo falhar): rode 'python scripts/lock_diario.py --finish --status done --slug <slug> --url <url-publicada>' se deu certo, ou '--status failed --nota \"<motivo em uma linha>\"' se nao deu. Regras que valem por cima de tudo: nenhuma imagem do artigo pode ser logo de marca ou grade de logos, e o estudo so e linkado por https://metakosmos.com.br/estudo, nunca pelo PDF direto. Ao terminar, imprima o slug, a URL publicada, a URL do post no LinkedIn e o resultado da auditoria." ^
 --dangerously-skip-permissions ^
 --add-dir "%BASE%" < NUL >> "%LOG%" 2>&1

REM O "< NUL" acima nao e enfeite: sob o Agendador de Tarefas nao existe console,
REM e sem redirecionar a entrada o CLI e morto na hora com STATUS_CONTROL_C_EXIT
REM (LastTaskResult 3221225786), sem escrever uma linha sequer no log.

set "RC=%ERRORLEVEL%"

REM --- rede de seguranca: se o agente morreu antes do passo 5, o lock nao pode
REM --- ficar em "running" para sempre. Marca failed (o --finish do agente, se
REM --- ja rodou, escreveu done e este comando so confirma o que ja esta la).
python "%BASE%\scripts\lock_diario.py" --show | findstr /C:"\"status\": \"running\"" >nul
if not errorlevel 1 (
    python "%BASE%\scripts\lock_diario.py" --finish --status failed --nota "agente terminou sem fechar o lock (exit=%RC%)" >> "%LOG%" 2>&1
)

echo.>> "%LOG%"
echo FIM %DATE% %TIME% (exit=%RC%)>> "%LOG%"
endlocal & exit /b %RC%
