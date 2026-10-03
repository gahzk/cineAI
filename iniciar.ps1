# CineAI: instala e inicia no Windows. Rode com o arquivo iniciar.bat (duplo clique).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "backend")

function Pare($msg) { Write-Host "`n$msg" -ForegroundColor Red; Read-Host "Aperte Enter para sair"; exit 1 }

# 1. Python 3.11 ou mais novo
$py = $null
foreach ($c in @("py -3", "python")) {
    try { $v = & ([scriptblock]::Create("$c -c `"import sys; print(sys.version_info >= (3, 11))`"")) 2>$null } catch { $v = $null }
    if ($v -eq "True") { $py = $c; break }
}
if (-not $py) { Pare "Python 3.11+ não encontrado. Instale em https://www.python.org/downloads/ marcando 'Add python.exe to PATH' e rode de novo." }

# 2. Ambiente virtual e dependências (só na primeira vez demora)
if (-not (Test-Path ".venv")) {
    Write-Host "Criando ambiente Python..."
    & ([scriptblock]::Create("$py -m venv .venv"))
}
$venvPy = ".\.venv\Scripts\python.exe"
Write-Host "Instalando dependências..."
& $venvPy -m pip install -q --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { Pare "Falha ao instalar as dependências." }

# 3. Configuração (.env), criada só na primeira vez
if (-not (Test-Path ".env")) {
    Write-Host "`nConfiguração inicial" -ForegroundColor Cyan
    $tmdb = Read-Host "Cole o 'API Read Access Token' do TMDB (themoviedb.org > Configurações > API)"
    if (-not $tmdb.Trim()) { Pare "Sem token do TMDB o CineAI não funciona." }
    $secret = & $venvPy -c "import secrets; print(secrets.token_hex(32))"
    $linhas = @("TMDB_TOKEN=$($tmdb.Trim())", "SECRET_KEY=$secret")

    $usarMysql = Read-Host "Usar o seu MySQL? (s/N; Enter usa SQLite, sem instalar nada)"
    if ($usarMysql -match "^[sS]") {
        $u = Read-Host "Usuário do MySQL (ex.: root)"
        $p = Read-Host "Senha do MySQL"
        $h = Read-Host "Servidor [localhost]"; if (-not $h) { $h = "localhost" }
        $d = Read-Host "Nome do banco [cineai] (crie antes: CREATE DATABASE cineai CHARACTER SET utf8mb4;)"
        if (-not $d) { $d = "cineai" }
        $linhas += "DATABASE_URL=mysql+pymysql://$([uri]::EscapeDataString($u)):$([uri]::EscapeDataString($p))@${h}:3306/${d}?charset=utf8mb4"
    }

    try {
        Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
        $linhas += "OLLAMA_MODEL=qwen3:4b"
        Write-Host "Ollama encontrado: busca por texto ligada (qwen3:4b)."
    } catch {
        Write-Host "Ollama não está aberto: a busca por texto fica desligada. Para ligar depois, adicione OLLAMA_MODEL=qwen3:4b em backend\.env"
    }
    [IO.File]::WriteAllLines((Join-Path $PWD ".env"), $linhas, (New-Object Text.UTF8Encoding $false))
    Write-Host "Configuração salva em backend\.env"
}

# 4. Conta de administrador (pergunta uma vez; a conta é criada quando o servidor sobe)
if (-not (Select-String -Path .env -Pattern '^ADMIN_EMAIL=' -Quiet)) {
    $adm = Read-Host "`nE-mail da sua conta de administrador (Enter para pular)"
    if ($adm.Trim()) {
        $sec = Read-Host "Senha dessa conta (mínimo 8 caracteres; use se a conta ainda não existir)" -AsSecureString
        $senha = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
        $extra = @("", "ADMIN_EMAIL=$($adm.Trim())")
        if ($senha) { $extra += "ADMIN_PASSWORD=$senha" }
        [IO.File]::AppendAllLines((Join-Path $PWD ".env"), [string[]]$extra, (New-Object Text.UTF8Encoding $false))
        Write-Host "Admin configurado. Entre no site com esse e-mail e veja a página Admin."
    }
}

# 5. Inicia
Write-Host "`nCineAI em http://localhost:8000  (feche esta janela para parar)" -ForegroundColor Green
Start-Process "http://localhost:8000"
& $venvPy -m uvicorn app.main:app --env-file .env
Read-Host "O servidor parou. Aperte Enter para sair"
