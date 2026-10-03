"""Senhas (bcrypt), tokens (JWT) e as dependências de usuário logado e admin."""
import time
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, TOKEN_DAYS
from app.db import User, get_db

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:  # hash corrompido ou senha acima de 72 bytes
        return False


def create_token(user_id: int) -> str:
    expires = datetime.now(UTC) + timedelta(days=TOKEN_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expires}, SECRET_KEY, algorithm="HS256")


def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Usuário do token, ou None sem token. Token inválido é 401 para o front saber que expirou."""
    if creds is None:
        return None
    try:
        user_id = int(jwt.decode(creds.credentials, SECRET_KEY, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Entre de novo.") from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado.")
    return user


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Entre na sua conta para usar este recurso.")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso restrito a administradores.")
    return user


# ---------------------------------------------------------------------------
# Limite simples de tentativas, em memória (um processo basta para este projeto)
# ---------------------------------------------------------------------------
_attempts: dict[str, list[float]] = {}


def check_rate(key: str, limit: int, window_s: int) -> None:
    """Levanta 429 quando `key` já registrou `limit` eventos na janela."""
    now = time.monotonic()
    recent = [t for t in _attempts.get(key, []) if now - t < window_s]
    _attempts[key] = recent
    if len(recent) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Espere alguns minutos.")


def record(key: str) -> None:
    _attempts.setdefault(key, []).append(time.monotonic())


def clear(key: str) -> None:
    _attempts.pop(key, None)
