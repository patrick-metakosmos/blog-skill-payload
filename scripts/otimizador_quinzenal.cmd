@echo off
REM ============================================================
REM otimizador_quinzenal.cmd - ciclo quinzenal do Otimizador do blog mK.
REM Chamado pela tarefa agendada "Blog mK - otimizador quinzenal"
REM (registrar/alterar: scripts\registrar_tarefa_otimizador.ps1).
REM Log: logs\otimizador-quinzenal-AAAA-MM-DD.log
REM
REM Mesmo desenho do artigo_diario.cmd (sem janela, prompt em arquivo, entrada
REM padrao redirecionada: sob o Agendador nao existe console e o CLI morre sem isso).
REM O prompt mora em scripts\otimizador\prompt_otimizador_quinzenal.md: editar la.
REM A trava (ciclo_guarda.py) impede rodar duas vezes o mesmo ciclo.
REM ============================================================
setlocal
chcp 65001 > nul
set "BASE=%~dp0.."
cd /d "%BASE%"
set "PYTHONIOENCODING=utf-8"
set "PROMPT=%BASE%\scripts\otimizador\prompt_otimizador_quinzenal.md"
if not exist "logs" mkdir "logs"
for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "HOJE=%%a"
set "LOG=%BASE%\logs\otimizador-quinzenal-%HOJE%.log"

echo ============================================================>> "%LOG%"
echo INICIO %DATE% %TIME% em %COMPUTERNAME%>> "%LOG%"
echo ============================================================>> "%LOG%"

if not exist "%PROMPT%" (
    echo ERRO: prompt nao encontrado em %PROMPT%>> "%LOG%"
    endlocal & exit /b 2
)

REM --- TRAVA: um ciclo por periodo ---
python "%BASE%\scripts\otimizador\ciclo_guarda.py" --check >> "%LOG%" 2>&1
if errorlevel 1 (
    echo SAINDO: o ciclo deste periodo ja foi feito ou esta rodando.>> "%LOG%"
    endlocal & exit /b 0
)

call "%APPDATA%\npm\claude.cmd" -p --dangerously-skip-permissions --add-dir "%BASE%" --add-dir "%BASE%\..\Mega_Brain" < "%PROMPT%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"

REM --- rede de seguranca: se o agente morreu antes do passo 5, a trava nao pode ficar em "running"
python "%BASE%\scripts\otimizador\ciclo_guarda.py" --show | findstr /C:"\"status\": \"running\"" >nul
if not errorlevel 1 (
    python "%BASE%\scripts\otimizador\ciclo_guarda.py" --finish failed --nota "agente terminou sem fechar a trava (exit=%RC%)" >> "%LOG%" 2>&1
)

REM aviso no Slack quando o ciclo falha (desde 24/11/2026)
set "FALHOU="
if not "%RC%"=="0" set "FALHOU=1"
python "%BASE%\scripts\otimizador\ciclo_guarda.py" --show | findstr /C:"\"status\": \"failed\"" >nul
if not errorlevel 1 set "FALHOU=1"
if defined FALHOU python "%BASE%\scripts\avisar_falha.py" otimizador "%LOG%" %RC% >> "%LOG%" 2>&1

echo.>> "%LOG%"
echo FIM %DATE% %TIME% (exit=%RC%)>> "%LOG%"
endlocal & exit /b %RC%
