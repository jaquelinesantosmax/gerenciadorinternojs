# Liga só o banco de dados (usado pelos testes automáticos).
. (Join-Path $PSScriptRoot 'comum.ps1')
$cfg = Obter-Config
Iniciar-Banco $cfg
Write-Host "Banco ligado na porta $($cfg.PG_PORTA)."
