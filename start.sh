#!/usr/bin/env bash
# =============================================================
#  CineAI — Launcher (Linux / macOS)
#  Uso: chmod +x start.sh && ./start.sh
# =============================================================
set -e

PINK='\033[38;5;198m'
TEAL='\033[38;5;37m'
GREEN='\033[38;5;42m'
YELLOW='\033[38;5;226m'
RED='\033[38;5;196m'
RESET='\033[0m'
BOLD='\033[1m'

banner() {
  echo -e "${PINK}"
  echo '  ██████╗██╗███╗   ██╗███████╗ █████╗ ██╗'
  echo ' ██╔════╝██║████╗  ██║██╔════╝██╔══██╗██║'
  echo ' ██║     ██║██╔██╗ ██║█████╗  ███████║██║'
  echo ' ██║     ██║██║╚██╗██║██╔══╝  ██╔══██║██║'
  echo ' ╚██████╗██║██║ ╚████║███████╗██║  ██║██║'
  echo '  ╚═════╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝'
  echo -e "${RESET}"
  echo -e "${BOLD}  Recomendador Inteligente de Filmes e Séries${RESET}"
  echo -e "  ============================================"
  echo ""
}

ok()   { echo -e "  ${GREEN}[OK]${RESET} $1"; }
info() { echo -e "  ${TEAL}[...]${RESET} $1"; }
warn() { echo -e "  ${YELLOW}[!]${RESET} $1"; }
err()  { echo -e "  ${RED}[ERRO]${RESET} $1"; exit 1; }

banner

# --- Verificar Python 3 ---
if ! command -v python3 &>/dev/null; then
  err "Python 3 não encontrado. Instale em: https://python.org"
fi
PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
ok "Python $PY_VER encontrado."

# --- Entrar na pasta backend ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

# --- Criar ambiente virtual ---
if [ ! -d ".venv" ]; then
  info "Criando ambiente virtual..."
  python3 -m venv .venv
  ok "Ambiente virtual criado."
fi

# --- Ativar ambiente virtual ---
source .venv/bin/activate

# --- Instalar dependências ---
info "Verificando dependências..."
if ! python3 -c "import fastapi" &>/dev/null 2>&1; then
  info "Instalando pacotes (primeira vez pode demorar 1-2 min)..."
  pip install -r requirements.txt --quiet
  ok "Dependências instaladas."
else
  ok "Dependências já instaladas."
fi

# --- Verificar / criar .env ---
if [ ! -f ".env" ]; then
  echo ""
  warn "Arquivo .env não encontrado."
  echo ""
  read -rp "  Cole seu TMDB Bearer Token aqui: " TMDB_TOKEN
  cat > .env <<EOF
TMDB_BEARER_TOKEN=${TMDB_TOKEN}
DATABASE_URL=sqlite+aiosqlite:///./cineai.db
SECRET_KEY=cineai-secret-mude-em-producao
ACCESS_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]
CATALOG_TARGET=2500
CACHE_EXPIRATION_DAYS=7
EOF
  ok "Arquivo .env criado."
fi

# --- Iniciar servidor ---
echo ""
info "Iniciando servidor CineAI na porta 8000..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!

# --- Aguardar servidor ficar pronto ---
info "Aguardando servidor ficar pronto..."
for i in $(seq 1 20); do
  sleep 1
  if curl -s http://localhost:8000/api/health &>/dev/null; then
    break
  fi
done

ok "Servidor pronto!"
echo ""
echo -e "  ${BOLD}Acesse:${RESET} ${PINK}http://localhost:8000${RESET}"
echo -e "  ${BOLD}API Docs:${RESET} ${TEAL}http://localhost:8000/api/docs${RESET}"
echo ""
echo -e "  Pressione ${BOLD}Ctrl+C${RESET} para encerrar."
echo -e "  ============================================"
echo ""

# --- Abrir navegador ---
if command -v xdg-open &>/dev/null; then
  xdg-open "http://localhost:8000/login" &>/dev/null &
elif command -v open &>/dev/null; then
  open "http://localhost:8000/login"
fi

# --- Manter processo ativo ---
wait $SERVER_PID
