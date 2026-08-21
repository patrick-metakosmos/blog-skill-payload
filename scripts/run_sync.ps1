# run_sync.ps1 - Sincronizacao agendada do banco de assets blog-mk
# Roda sync_assets.py + render_views.py. Avaliacao VISUAL e feita por Claude numa sessao.
# Paths derivados de $PSScriptRoot para evitar problemas de encoding com acentos.

$ErrorActionPreference = "Continue"

# scripts/ -> skill dir -> desktop dir (Area de Trabalho)
$scriptsDir = $PSScriptRoot
$skill      = Split-Path $scriptsDir -Parent
$desktop    = Split-Path $skill -Parent
$python     = Join-Path $desktop "Video_Image_Plus\venv\Scripts\python.exe"
$log        = Join-Path $skill "references\sync-cron.log"

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $log -Value "[$ts] Iniciando sync de assets..." -Encoding utf8

Set-Location $skill
& $python (Join-Path $scriptsDir "sync_assets.py")  *>> $log
& $python (Join-Path $scriptsDir "render_views.py") *>> $log

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $log -Value "[$ts] Sync concluido." -Encoding utf8
