<#
    registrar_tarefa_diaria.ps1 - registra (ou re-registra) a tarefa do Windows que
    dispara 1 artigo do blog mK por dia de manha.

    Uso:
        powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1
        powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Hora 06:30
        powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Remover

    StartWhenAvailable: se o PC estiver desligado as 7h, a tarefa roda assim que ligar.
    Roda so no usuario logado (precisa da sessao do Claude Code autenticada).
#>
param(
    [string]$Hora = "07:00",
    [string]$Nome = "Blog mK - artigo diario",
    [switch]$Remover
)

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $PSScriptRoot
$cmd  = Join-Path $PSScriptRoot "artigo_diario.cmd"

if ($Remover) {
    Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
    Write-Output "Tarefa '$Nome' removida."
    return
}

if (-not (Test-Path $cmd)) { throw "Nao achei $cmd" }

$action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$cmd`"" -WorkingDirectory $base
$trigger = New-ScheduledTaskTrigger -Daily -At $Hora
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $Nome -Action $action -Trigger $trigger -Settings $settings `
    -Description "Gera, audita e publica 1 artigo do blog metaKosmos por dia (skill blog-mk-payload), e posta no LinkedIn." `
    -Force | Out-Null

$t = Get-ScheduledTaskInfo -TaskName $Nome
Write-Output "Tarefa '$Nome' registrada para $Hora todo dia."
Write-Output "Proxima execucao: $($t.NextRunTime)"
Write-Output "Rodar agora:   Start-ScheduledTask -TaskName '$Nome'"
Write-Output "Log do dia:    $base\logs\artigo-diario-<AAAA-MM-DD>.log"
