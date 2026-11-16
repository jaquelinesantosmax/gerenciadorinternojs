# Liga o Gerenciador inteiro no computador: banco de dados, servidor e telas.
# Depois abre o navegador em http://localhost:3000
. (Join-Path $PSScriptRoot 'comum.ps1')

Write-Host ''
Write-Host 'Ligando o Gerenciador...' -ForegroundColor Green

$cfg = Obter-Config
Iniciar-Banco $cfg
Preparar-Backend
Preparar-Frontend

# Configuração do servidor (vale para os programas abertos a partir daqui).
$env:GERENCIADOR_DATABASE_URL = Url-Banco $cfg 'gerenciador'
$env:GERENCIADOR_AMBIENTE = 'desenvolvimento'
$env:GERENCIADOR_LOGIN_TESTE_HABILITADO = 'true'
$env:BACKEND_URL = "http://127.0.0.1:$($cfg.BACKEND_PORTA)"

Escrever-Passo 'Atualizando as tabelas do banco'
Push-Location (Join-Path $Raiz 'backend')
try {
    $codigo = Executar-Com-Log (Join-Path $Raiz 'backend\.venv\Scripts\alembic.exe') @('upgrade', 'head') (Join-Path $Logs 'migracoes.log')
    if ($codigo -ne 0) { throw 'Falha ao atualizar o banco. Veja infra\logs\migracoes.log' }
} finally { Pop-Location }

function Respondendo([string]$url) {
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $url | Out-Null; return $true } catch { return $false }
}

$processos = @{}
if (Test-Path $ArquivoProcessos) {
    $anteriores = Get-Content $ArquivoProcessos | ConvertFrom-Json
    foreach ($p in $anteriores.PSObject.Properties) { $processos[$p.Name] = $p.Value }
}

$urlBackend = "http://127.0.0.1:$($cfg.BACKEND_PORTA)/api/saude"
if (-not (Respondendo $urlBackend)) {
    Escrever-Passo 'Ligando o servidor'
    $p = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory (Join-Path $Raiz 'backend') `
        -FilePath $Python -ArgumentList @('-m', 'uvicorn', 'gerenciador.principal:criar_app', '--factory',
            '--host', '127.0.0.1', '--port', $cfg.BACKEND_PORTA, '--reload') `
        -RedirectStandardOutput (Join-Path $Logs 'servidor.log') -RedirectStandardError (Join-Path $Logs 'servidor-erros.log')
    $processos['servidor'] = $p.Id
}

$urlFrontend = "http://localhost:$($cfg.FRONTEND_PORTA)"
if (-not (Respondendo "$urlFrontend/entrar")) {
    Escrever-Passo 'Ligando as telas'
    $p = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory (Join-Path $Raiz 'frontend') `
        -FilePath (Join-Path $NodeDir 'npm.cmd') -ArgumentList @('run', 'dev', '--', '--port', $cfg.FRONTEND_PORTA) `
        -RedirectStandardOutput (Join-Path $Logs 'telas.log') -RedirectStandardError (Join-Path $Logs 'telas-erros.log')
    $processos['telas'] = $p.Id
}
$processos | ConvertTo-Json | Set-Content $ArquivoProcessos

Escrever-Passo 'Esperando tudo responder'
foreach ($i in 1..90) {
    if ((Respondendo $urlBackend) -and (Respondendo "$urlFrontend/entrar")) { break }
    Start-Sleep -Seconds 1
}
if (-not (Respondendo $urlBackend)) { throw 'O servidor não respondeu. Veja infra\logs\servidor-erros.log' }
if (-not (Respondendo "$urlFrontend/entrar")) { throw 'As telas não responderam. Veja infra\logs\telas-erros.log' }

Write-Host ''
Write-Host "Pronto! O Gerenciador está em $urlFrontend" -ForegroundColor Green
Write-Host 'Para desligar, rode infra\desligar.cmd'
if (-not $env:GERENCIADOR_NAO_ABRIR_NAVEGADOR) { Start-Process $urlFrontend }
