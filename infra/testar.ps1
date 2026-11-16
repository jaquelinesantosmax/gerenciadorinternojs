# Roda todos os testes automáticos: servidor (Python) e telas (Next.js).
. (Join-Path $PSScriptRoot 'comum.ps1')
$ErrorActionPreference = 'Continue'

$cfg = Obter-Config
Iniciar-Banco $cfg
Preparar-Backend
Preparar-Frontend

Write-Host ''
Write-Host 'Testes do servidor' -ForegroundColor Green
Push-Location (Join-Path $Raiz 'backend')
& $Python -m pytest -p no:warnings
$servidor = $LASTEXITCODE
& (Join-Path $Raiz 'backend\.venv\Scripts\ruff.exe') check .
$estilo = $LASTEXITCODE
Pop-Location

Write-Host ''
Write-Host 'Testes das telas' -ForegroundColor Green
Push-Location (Join-Path $Raiz 'frontend')
& (Join-Path $NodeDir 'npx.cmd') tsc --noEmit
$tipos = $LASTEXITCODE
& (Join-Path $NodeDir 'npx.cmd') vitest run
$telas = $LASTEXITCODE
Pop-Location

Write-Host ''
if ($servidor -eq 0 -and $estilo -eq 0 -and $tipos -eq 0 -and $telas -eq 0) {
    Write-Host 'Todos os testes passaram.' -ForegroundColor Green
} else {
    Write-Host 'Algum teste falhou. Veja as mensagens acima.' -ForegroundColor Red
    exit 1
}
