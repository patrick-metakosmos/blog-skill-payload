<#
    registrar_tarefa_diaria.ps1 - registra (ou re-registra) a tarefa do Windows que
    dispara 1 artigo do blog mK por dia de manha.

    Uso:
        powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1
        powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Hora 06:30
        powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Remover

    StartWhenAvailable: se o PC estiver desligado as 7h, a tarefa roda assim que ligar.
    Roda so no usuario logado (precisa da sessao do Claude Code autenticada).

    -Hora aceita mais de um horario. Util para repescagem: se a outra maquina
    pegou o lock e travou, a rodada mais tarde assume (ver --stale-hours em
    lock_diario.py). A trava garante que so sai 1 artigo por dia de qualquer jeito.
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

# conhost --headless: cria o console que o cmd precisa, mas SEM janela. Antes a
# tarefa abria um cmd em branco na tela, e fechar essa janela matava o artigo no
# meio (trava presa em "running" por 3h). Continua rodando no usuario logado de
# proposito: o git push da trava usa as credenciais do Gerenciador de Credenciais
# dele, que uma tarefa "executar com usuario deslogado" nao enxerga.
# Acompanhar: logs\artigo-diario-<data>.log | Parar: Stop-ScheduledTask -TaskName $Nome
#
# SEM ASPAS e com caminho RELATIVO ao WorkingDirectory, de proposito: o conhost
# reinterpreta a linha de comando e estraga aspas aninhadas. Com o caminho
# absoluto entre aspas (a pasta tem espacos e acento), o .cmd simplesmente nao
# era chamado e a tarefa saia com codigo 0 em 6 segundos. "scripts\artigo_diario.cmd"
# nao tem espaco, e o .cmd acha a propria pasta sozinho via %~dp0.
$action  = New-ScheduledTaskAction -Execute "conhost.exe" -Argument "--headless cmd.exe /c scripts\artigo_diario.cmd" -WorkingDirectory $base
$horas = @($Hora -split '[,;]' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($horas.Count -eq 0) { throw "Nenhum horario valido em -Hora '$Hora'" }
$trigger = @($horas | ForEach-Object { New-ScheduledTaskTrigger -Daily -At ([datetime]::Parse($_)) })
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
Write-Output "Tarefa '$Nome' registrada para $($horas -join ', ') todo dia."
Write-Output "Proxima execucao: $($t.NextRunTime)"
Write-Output "Rodar agora:   Start-ScheduledTask -TaskName '$Nome'"
Write-Output "Log do dia:    $base\logs\artigo-diario-<AAAA-MM-DD>.log"
