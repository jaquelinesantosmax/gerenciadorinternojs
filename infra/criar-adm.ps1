# Cadastra um ADM da plataforma direto no banco (uso na instalação).
# Uso: infra\criar-adm.cmd   (pergunta e-mail e nome)
. (Join-Path $PSScriptRoot 'comum.ps1')

$cfg = Obter-Config
Iniciar-Banco $cfg
Preparar-Backend

$email = Read-Host 'E-mail (@jusbrasil.com.br ou @digesto.com.br)'
$nome = Read-Host 'Nome completo'

$env:GERENCIADOR_DATABASE_URL = Url-Banco $cfg 'gerenciador'
Push-Location (Join-Path $Raiz 'backend')
try {
    Executar-Com-Log (Join-Path $Raiz 'backend\.venv\Scripts\alembic.exe') @('upgrade', 'head') (Join-Path $Logs 'migracoes.log') | Out-Null
    & $Python -m gerenciador.cli criar-adm --email $email --nome $nome
} finally { Pop-Location }
