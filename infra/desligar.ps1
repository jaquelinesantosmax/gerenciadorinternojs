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
# Garantia: encerra qualquer programa que tenha ficado preso nas portas do sistema (ex.: um servidor antigo).
$cfg = Obter-Config
foreach ($porta in $cfg.BACKEND_PORTA, $cfg.FRONTEND_PORTA) {
    $donos = Get-NetTCPConnection -LocalPort ([int]$porta) -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid_ in $donos) {
        Executar-Com-Log 'taskkill.exe' @('/PID', [string]$pid_, '/T', '/F') (Join-Path $Logs 'desligar.log') | Out-Null
    }
}
Parar-Banco
Escrever-Passo 'Desligado: banco de dados'
Write-Host 'Pronto.' -ForegroundColor Green
