"""Configuração lida das variáveis de ambiente (carregue o .env com `uvicorn --env-file .env`)."""
import os

_OLD_DEFAULT_KEY = "change-me-in-production-use-secrets"


def _secret_key() -> str:
    key = os.getenv("SECRET_KEY", "").strip()
    if not key or key == _OLD_DEFAULT_KEY:
        raise RuntimeError(
            "Defina SECRET_KEY no .env. Gere uma com: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
    return key


SECRET_KEY = _secret_key()
TOKEN_DAYS = int(os.getenv("TOKEN_DAYS", "7"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cineai.db")

# TMDB_BEARER_TOKEN é o nome antigo; continua aceito para não quebrar .env existentes.
TMDB_TOKEN = (os.getenv("TMDB_TOKEN") or os.getenv("TMDB_BEARER_TOKEN") or "").strip()

# Busca em linguagem natural. Sem chave, o recurso fica desligado e o formulário continua funcionando.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
AI_MODEL = os.getenv("CINEAI_MODEL", "claude-opus-5-5")

# Alternativa gratuita: um modelo rodando no Ollama do próprio computador (tem prioridade sobre o Claude).
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")

# Conta de administrador. Com as duas, a conta é criada na primeira vez que o servidor sobe;
# só com o e-mail, quem se cadastrar com ele vira admin.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
