# Medição das otimizações do blog (agendada no Agendador de Tarefas do Windows).
# Roda o medir.py, guarda a saída em logs\medicao.log e abre o Log de Otimizações.
# Enquanto o robô não estiver no Search Console, a leitura usa o login do Patrick
# (plano B), que o Workspace da mK expira em horas: se o medir.py sair com código 3,
# abre o login do Google no navegador, espera a autorização e tenta uma vez mais.
$base = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$env:PYTHONIOENCODING = "utf-8"
$log = Join-Path $base "logs\medicao.log"
"`n==== $(Get-Date -Format 'yyyy-MM-dd HH:mm') ====" | Out-File -FilePath $log -Append -Encoding utf8
Set-Location $base
python "scripts\otimizador\medir.py" *>&1 | Out-File -FilePath $log -Append -Encoding utf8
if ($LASTEXITCODE -eq 3) {
    "login expirado: abrindo o navegador para renovar" | Out-File -FilePath $log -Append -Encoding utf8
    $env:CLOUDSDK_CONFIG = Join-Path $base "credenciais\gcloud-gsc"
    gcloud auth application-default login --scopes="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/webmasters.readonly" *>&1 | Out-File -FilePath $log -Append -Encoding utf8
    Remove-Item Env:\CLOUDSDK_CONFIG
    python "scripts\otimizador\medir.py" *>&1 | Out-File -FilePath $log -Append -Encoding utf8
}
Start-Process "https://docs.google.com/spreadsheets/d/10XRM5Vgy2AHYkPVYdcshgmM4WqcqYywnjbsrGtp2RQI/edit"
