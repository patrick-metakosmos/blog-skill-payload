# Medição das otimizações do blog (agendada no Agendador de Tarefas do Windows).
# Roda o medir.py, guarda a saída em logs\medicao.log e abre o Log de Otimizações.
$base = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$env:PYTHONIOENCODING = "utf-8"
$log = Join-Path $base "logs\medicao.log"
"`n==== $(Get-Date -Format 'yyyy-MM-dd HH:mm') ====" | Out-File -FilePath $log -Append -Encoding utf8
Set-Location $base
python "scripts\otimizador\medir.py" *>&1 | Out-File -FilePath $log -Append -Encoding utf8
Start-Process "https://docs.google.com/spreadsheets/d/10XRM5Vgy2AHYkPVYdcshgmM4WqcqYywnjbsrGtp2RQI/edit"
