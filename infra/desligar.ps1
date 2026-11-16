# Desliga as telas, o servidor e o banco de dados.
. (Join-Path $PSScriptRoot 'comum.ps1')

Write-Host 'Desligando o Gerenciador...' -ForegroundColor Green
if (Test-Path $ArquivoProcessos) {
    $processos = Get-Content $ArquivoProcessos | ConvertFrom-Json
    foreach ($p in $processos.PSObject.Properties) {
        # /T encerra também os programas abertos por ele (o servidor e as telas abrem processos filhos).
        Executar-Com-Log 'taskkill.exe' @('/PID', [string]$p.Value, '/T', '/F') (Join-Path $Logs 'desligar.log') | Out-Null
        Escrever-Passo "Desligado: $($p.Name)"
    }
    Remove-Item $ArquivoProcessos
}
Parar-Banco
Escrever-Passo 'Desligado: banco de dados'
Write-Host 'Pronto.' -ForegroundColor Green
