@echo off
REM ============================================================
REM artigo_diario.cmd - dispara 1 artigo do blog mK por dia.
REM Chamado pela tarefa agendada "Blog mK - artigo diario" (07:00).
REM Registrar/alterar: scripts\registrar_tarefa_diaria.ps1
REM Log: logs\artigo-diario-AAAA-MM-DD.log
REM ============================================================
setlocal
set "BASE=%~dp0.."
cd /d "%BASE%"
set "PYTHONIOENCODING=utf-8"

if not exist "logs" mkdir "logs"
for /f "tokens=1-3 delims=/-. " %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "HOJE=%%a"
set "LOG=%BASE%\logs\artigo-diario-%HOJE%.log"

echo ============================================================>> "%LOG%"
echo INICIO %DATE% %TIME%>> "%LOG%"
echo ============================================================>> "%LOG%"

call "%APPDATA%\npm\claude.cmd" -p ^
 "Rode a skill blog-mk-payload de ponta a ponta, sozinho, sem me perguntar nada. Passo 1: rode 'python scripts/status_backlog.py' e pegue a PRIMEIRA pauta ainda pendente (a fazer) do 'Pautas e Palavras Cahve/BACKLOG-EDITORIAL.md' - se a primeira tiver aviso de sobreposicao/canibalizacao, pule para a proxima limpa. Passo 2: escreva o artigo completo seguindo TODOS os pisos duros da skill (2000+ palavras de corpo, FAQ 10+, zero em dash, keyword exata abrindo o H1, citacao do State of Immersive & Agentic Commerce 2026 conferida na origem). Passo 3: rode 'python scripts/audit_artigo.py <slug>' e so siga com ZERO falhas - se alguma checagem bloqueadora falhar, corrija e re-rode; nenhum bloqueador pode ser relevado, porque nao ha revisao humana antes do publico. Passo 4: publique AO VIVO e poste no LinkedIn, nessa ordem. Regras que valem por cima de tudo: nenhuma imagem do artigo pode ser logo de marca ou grade de logos, e o estudo so e linkado por https://metakosmos.com.br/estudo, nunca pelo PDF direto. Ao terminar, imprima o slug, a URL publicada, a URL do post no LinkedIn e o resultado da auditoria." ^
 --dangerously-skip-permissions ^
 --add-dir "%BASE%" >> "%LOG%" 2>&1

set "RC=%ERRORLEVEL%"
echo.>> "%LOG%"
echo FIM %DATE% %TIME% (exit=%RC%)>> "%LOG%"
endlocal & exit /b %RC%
