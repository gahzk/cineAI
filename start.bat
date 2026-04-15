@echo off
chcp 65001 >nul
title CineAI — Iniciando...
color 0D

echo.
echo  ██████╗██╗███╗   ██╗███████╗ █████╗ ██╗
echo ██╔════╝██║████╗  ██║██╔════╝██╔══██╗██║
echo ██║     ██║██╔██╗ ██║█████╗  ███████║██║
echo ██║     ██║██║╚██╗██║██╔══╝  ██╔══██║██║
echo ╚██████╗██║██║ ╚████║███████╗██║  ██║██║
echo  ╚═════╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝
echo.
echo  Recomendador Inteligente de Filmes e Series
echo  ============================================
echo.

:: --- Verificar Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Baixe em: https://www.python.org/downloads/
    echo Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% encontrado.

:: --- Entrar na pasta backend ---
cd /d "%~dp0..\backend"

:: --- Criar ambiente virtual se nao existir ---
if not exist ".venv" (
    echo.
    echo [...] Criando ambiente virtual...
    python -m venv .venv
    echo [OK] Ambiente virtual criado.
)

:: --- Ativar ambiente virtual ---
call .venv\Scripts\activate.bat

:: --- Instalar dependencias ---
echo.
echo [...] Verificando dependencias...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo [...] Instalando pacotes (primeira vez pode demorar 1-2 min)...
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas.
) else (
    echo [OK] Dependencias ja instaladas.
)

:: --- Verificar / criar .env ---
if not exist ".env" (
    echo.
    echo [ATENCAO] Arquivo .env nao encontrado.
    echo.
    set /p TMDB_TOKEN="Cole seu TMDB Bearer Token aqui: "
    (
        echo TMDB_BEARER_TOKEN=!TMDB_TOKEN!
        echo DATABASE_URL=sqlite+aiosqlite:///./cineai.db
        echo SECRET_KEY=cineai-secret-mude-em-producao
        echo ACCESS_TOKEN_EXPIRE_MINUTES=10080
        echo CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]
        echo CATALOG_TARGET=2500
        echo CACHE_EXPIRATION_DAYS=7
    ) > .env
    echo [OK] Arquivo .env criado.
)

:: --- Iniciar servidor em segundo plano ---
echo.
echo [...] Iniciando servidor CineAI...
start /b uvicorn app.main:app --host 127.0.0.1 --port 8000

:: --- Aguardar servidor subir ---
echo [...] Aguardando servidor ficar pronto...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel% neq 0 goto wait_loop

:: --- Abrir navegador ---
echo [OK] Servidor pronto!
echo.
echo  Acessando: http://localhost:8000
echo.
start http://localhost:8000/login

echo  Pressione Ctrl+C para encerrar o servidor.
echo  ============================================
echo.

:: --- Manter janela aberta exibindo logs ---
uvicorn app.main:app --host 127.0.0.1 --port 8000
