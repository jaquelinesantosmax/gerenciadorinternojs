# Funções usadas por ligar.ps1, desligar.ps1 e pelos testes.
# Tudo roda sem permissão de administrador: o banco é ligado como um programa comum, não como serviço.

$ErrorActionPreference = 'Stop'

$Raiz = Split-Path -Parent $PSScriptRoot
$Ferramentas = Join-Path $env:USERPROFILE 'ferramentas'
$PgBin = Join-Path $Ferramentas 'postgresql\bin'
$NodeDir = Join-Path $Ferramentas 'node'
$Dados = Join-Path $PSScriptRoot 'dados'
$Logs = Join-Path $PSScriptRoot 'logs'
$ArquivoEnv = Join-Path $PSScriptRoot '.env'
$ArquivoProcessos = Join-Path $Logs 'processos.json'
$Python = Join-Path $Raiz 'backend\.venv\Scripts\python.exe'

$env:Path = "$NodeDir;$PgBin;$env:Path"
New-Item -ItemType Directory -Force $Logs | Out-Null

function Escrever-Passo([string]$texto) { Write-Host "  > $texto" -ForegroundColor DarkGreen }

function Executar-Com-Log([string]$programa, [string[]]$argumentos, [string]$arquivoLog) {
    # No Windows PowerShell, redirecionar a saída de erro de um programa com 'Stop' ligado
    # interrompe o script na primeira mensagem, mesmo sem erro de verdade. Por isso o 'Continue' aqui.
    $anterior = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & $programa @argumentos *> $arquivoLog; return $LASTEXITCODE }
    finally { $ErrorActionPreference = $anterior }
}

function Obter-Config {
    # Cria a configuração local na primeira vez, com uma senha aleatória para o banco.
    # O arquivo infra/.env nunca vai para o GitHub.
    if (-not (Test-Path $ArquivoEnv)) {
        $caracteres = [char[]]'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        $senha = -join (1..28 | ForEach-Object { $caracteres | Get-Random })
        @(
            '# Configuracao local do Gerenciador. Nao enviar ao GitHub.'
            'PG_PORTA=5433'
            'PG_USUARIO=gerenciador'
            "PG_SENHA=$senha"
            'BACKEND_PORTA=8000'
            'FRONTEND_PORTA=3000'
        ) | Set-Content -Encoding ascii $ArquivoEnv
    }
    $cfg = @{}
    Get-Content $ArquivoEnv | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object {
        $partes = $_.Split('=', 2); $cfg[$partes[0].Trim()] = $partes[1].Trim()
    }
    return $cfg
}

function Url-Banco($cfg, [string]$nomeBanco) {
    return "postgresql+psycopg://$($cfg.PG_USUARIO):$($cfg.PG_SENHA)@localhost:$($cfg.PG_PORTA)/$nomeBanco"
}

function Banco-Ligado($cfg) {
    & (Join-Path $PgBin 'pg_isready.exe') -h localhost -p $cfg.PG_PORTA -q
    return $LASTEXITCODE -eq 0
}

function Iniciar-Banco($cfg) {
    if (-not (Test-Path (Join-Path $Dados 'PG_VERSION'))) {
        Escrever-Passo 'Criando o banco de dados pela primeira vez'
        if (Test-Path $Dados) { Remove-Item -Recurse -Force $Dados }  # sobra de uma tentativa que falhou
        # Arquivo temporário com a senha, apagado logo depois (fica em infra\logs, fora do GitHub).
        $arquivoSenha = Join-Path $Logs ("pw-" + [guid]::NewGuid() + '.txt')
        [IO.File]::WriteAllText($arquivoSenha, $cfg.PG_SENHA)
        try {
            $codigo = Executar-Com-Log (Join-Path $PgBin 'initdb.exe') @(
                '-D', $Dados, '-U', $cfg.PG_USUARIO, "--pwfile=$arquivoSenha",
                '-A', 'scram-sha-256', '-E', 'UTF8', '--locale=C'
            ) (Join-Path $Logs 'initdb.log')
            if ($codigo -ne 0) { throw "Falha ao criar o banco. Veja infra\logs\initdb.log" }
        } finally { Remove-Item -Force $arquivoSenha -ErrorAction SilentlyContinue }
    }
    if (-not (Banco-Ligado $cfg)) {
        Escrever-Passo 'Ligando o banco de dados'
        $opcoes = "-p $($cfg.PG_PORTA) -c listen_addresses=localhost"
        Start-Process -FilePath (Join-Path $PgBin 'pg_ctl.exe') -WindowStyle Hidden -ArgumentList @(
            'start', '-D', "`"$Dados`"", '-l', "`"$(Join-Path $Logs 'banco.log')`"", '-o', "`"$opcoes`""
        )
        foreach ($i in 1..60) { if (Banco-Ligado $cfg) { break }; Start-Sleep -Milliseconds 500 }
        if (-not (Banco-Ligado $cfg)) { throw 'O banco não ligou. Veja infra\logs\banco.log' }
    }
    $env:PGPASSWORD = $cfg.PG_SENHA
    foreach ($nome in 'gerenciador', 'gerenciador_teste') {
        $existe = & (Join-Path $PgBin 'psql.exe') -h localhost -p $cfg.PG_PORTA -U $cfg.PG_USUARIO -d postgres -tAc "select 1 from pg_database where datname='$nome'"
        if ($existe -ne '1') {
            & (Join-Path $PgBin 'createdb.exe') -h localhost -p $cfg.PG_PORTA -U $cfg.PG_USUARIO -E UTF8 $nome
        }
    }
    Remove-Item Env:PGPASSWORD
}

function Parar-Banco {
    if (Test-Path (Join-Path $Dados 'PG_VERSION')) {
        Executar-Com-Log (Join-Path $PgBin 'pg_ctl.exe') @('stop', '-D', $Dados, '-m', 'fast') (Join-Path $Logs 'parar-banco.log') | Out-Null
    }
}

function Preparar-Backend {
    if (-not (Test-Path $Python)) {
        Escrever-Passo 'Preparando o servidor (primeira vez, pode levar alguns minutos)'
        $pyInstalado = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
        & $pyInstalado -m venv (Join-Path $Raiz 'backend\.venv')
    }
    $marca = Join-Path $Raiz 'backend\.venv\requisitos.ok'
    $req = Join-Path $Raiz 'backend\requirements-dev.txt'
    $reqBase = Join-Path $Raiz 'backend\requirements.txt'
    $atual = (Get-FileHash $req).Hash + (Get-FileHash $reqBase).Hash
    if (-not (Test-Path $marca) -or (Get-Content $marca) -ne $atual) {
        Escrever-Passo 'Instalando as bibliotecas do servidor'
        & $Python -m pip install -q -r $req
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as bibliotecas do servidor.' }
        Set-Content $marca $atual
    }
}

function Preparar-Frontend {
    $front = Join-Path $Raiz 'frontend'
    $marca = Join-Path $front 'node_modules\.instalado'
    $atual = (Get-FileHash (Join-Path $front 'package-lock.json')).Hash
    if (-not (Test-Path $marca) -or (Get-Content $marca) -ne $atual) {
        Escrever-Passo 'Instalando as bibliotecas das telas (primeira vez, pode levar alguns minutos)'
        Push-Location $front
        try { & (Join-Path $NodeDir 'npm.cmd') ci --no-audit --no-fund --loglevel=error } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as bibliotecas das telas.' }
        Set-Content $marca $atual
    }
}
