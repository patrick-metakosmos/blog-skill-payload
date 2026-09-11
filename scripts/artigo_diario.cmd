@echo off
REM ============================================================
REM artigo_diario.cmd - dispara 1 artigo do blog mK por dia.
REM Roda nas DUAS maquinas (Patrick e estagiaria) sem duplicar:
REM lock_diario.py --acquire crava o lock do dia via push no GitHub,
REM e quem perde a corrida sai sem fazer nada.
REM Chamado pela tarefa agendada "Blog mK - artigo diario".
REM Registrar/alterar: scripts\registrar_tarefa_diaria.ps1
REM Log: logs\artigo-diario-AAAA-MM-DD.log
REM
REM   artigo_diario.cmd          producao: trava, gera, publica
REM   artigo_diario.cmd teste    teste de fumaca: MESMA chamada do CLI, com um
REM                              prompt que so prova as permissoes. Nao pega a
REM                              trava, nao publica. Log: logs\teste-permissoes-*.log
REM
REM O PROMPT MORA EM ARQUIVO (prompt_artigo_diario.md) e entra pela entrada
REM padrao. Duas razoes, as duas aprendidas em producao:
REM  1. Sob o Agendador nao existe console. Sem redirecionar a entrada, o CLI e
REM     morto na hora com STATUS_CONTROL_C_EXIT (3221225786). [falha de 10/09]
REM  2. Prompt inline passa pelo parser do cmd, onde \" NAO escapa aspas: a
REM     string fechou no meio, os flags viraram texto do prompt e o agente subiu
REM     sem permissao para nada. [falha de 11/09]
REM Editar o prompt: mexa no .md, nunca volte a coloca-lo aqui dentro.
REM ============================================================
setlocal
REM UTF-8 no console, senao os acentos saem ilegiveis no log
chcp 65001 > nul
set "BASE=%~dp0.."
cd /d "%BASE%"
set "PYTHONIOENCODING=utf-8"
set "MODO=%~1"

if not exist "logs" mkdir "logs"
for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "HOJE=%%a"

if /i "%MODO%"=="teste" (
    set "PROMPT=%BASE%\scripts\prompt_teste_permissoes.md"
    set "LOG=%BASE%\logs\teste-permissoes-%HOJE%.log"
) else (
    set "PROMPT=%BASE%\scripts\prompt_artigo_diario.md"
    set "LOG=%BASE%\logs\artigo-diario-%HOJE%.log"
)

echo ============================================================>> "%LOG%"
echo INICIO %DATE% %TIME% em %COMPUTERNAME% (modo: %MODO%)>> "%LOG%"
echo ============================================================>> "%LOG%"

if not exist "%PROMPT%" (
    echo ERRO: prompt nao encontrado em %PROMPT%>> "%LOG%"
    endlocal & exit /b 2
)

if /i "%MODO%"=="teste" goto :rodar

REM --- TRAVA: so uma maquina por dia passa daqui ---
python "%BASE%\scripts\lock_diario.py" --acquire >> "%LOG%" 2>&1
if errorlevel 1 (
    echo SAINDO: artigo de hoje ja foi feito ou outra maquina esta rodando.>> "%LOG%"
    endlocal & exit /b 0
)

:rodar
call "%APPDATA%\npm\claude.cmd" -p --dangerously-skip-permissions --add-dir "%BASE%" < "%PROMPT%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"

if /i "%MODO%"=="teste" goto :fim

REM --- rede de seguranca: se o agente morreu antes do passo 5, o lock nao pode
REM --- ficar em "running" para sempre. Marca failed (o --finish do agente, se
REM --- ja rodou, escreveu done e este comando so confirma o que ja esta la).
python "%BASE%\scripts\lock_diario.py" --show | findstr /C:"\"status\": \"running\"" >nul
if not errorlevel 1 (
    python "%BASE%\scripts\lock_diario.py" --finish --status failed --nota "agente terminou sem fechar o lock (exit=%RC%)" >> "%LOG%" 2>&1
)

:fim
echo.>> "%LOG%"
echo FIM %DATE% %TIME% (exit=%RC%)>> "%LOG%"
endlocal & exit /b %RC%
