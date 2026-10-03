"""CineAI: API JSON em /api e o frontend estático em /, no mesmo processo.

As rotas são `def` (não `async def`) de propósito: o FastAPI roda cada uma numa thread,
então uma chamada lenta ao TMDB não trava as outras requisições.
"""
from collections import Counter
from contextlib import asynccontextmanager
from datetime import UTC
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auth, nl, tmdb
from app.db import History, User, get_db, init_db
from app.ranking import Filters, recommend

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CineAI", version="3.0.0", docs_url="/api/docs", redoc_url=None,
              openapi_url="/api/openapi.json", lifespan=lifespan)


@app.exception_handler(tmdb.TMDBError)
def tmdb_error(_: Request, exc: tmdb.TMDBError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Modelos de entrada e saída
# ---------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class TextSearchIn(BaseModel):
    text: str = Field(min_length=3, max_length=300)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    is_admin: bool


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
@app.post("/api/auth/register", response_model=TokenOut, status_code=201, tags=["auth"])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(400, "Este e-mail já tem conta.")
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(400, "Este nome de usuário já está em uso.")
    user = User(email=body.email, username=body.username, hashed_password=auth.hash_password(body.password))
    db.add(user)
    db.commit()
    return TokenOut(access_token=auth.create_token(user.id))


@app.post("/api/auth/login", response_model=TokenOut, tags=["auth"])
def login(body: LoginIn, db: Session = Depends(get_db)):
    key = f"login:{body.email.lower()}"
    auth.check_rate(key, limit=10, window_s=15 * 60)
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not auth.verify_password(body.password, user.hashed_password):
        auth.record(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    auth.clear(key)
    return TokenOut(access_token=auth.create_token(user.id))


@app.get("/api/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(auth.current_user)):
    return user


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------
@app.get("/api/options", tags=["busca"])
def options():
    """Listas para montar o formulário: gêneros, streaming e se a busca por texto está ligada."""
    genres = sorted(tmdb.genres("movie").items(), key=lambda g: g[1])
    return {
        "genres": [{"id": gid, "name": name} for gid, name in genres],
        "providers": tmdb.providers(),
        "text_search": nl.enabled(),
    }


@app.post("/api/search", tags=["busca"])
def search(f: Filters, user: User | None = Depends(auth.optional_user), db: Session = Depends(get_db)):
    """Top 3 para os filtros. Logado, o resultado entra no histórico."""
    results, total = recommend(f)
    if user and results:
        _save_history(db, user, results)
    return {"results": results, "total_candidates": total, "filters": f}


@app.post("/api/search/text", tags=["busca"])
def search_text(body: TextSearchIn, user: User = Depends(auth.current_user), db: Session = Depends(get_db)):
    """Pedido em linguagem natural -> filtros (Claude) -> mesma busca do formulário."""
    key = f"ai:{user.id}"
    auth.check_rate(key, limit=20, window_s=60 * 60)
    auth.record(key)
    try:
        f = nl.text_to_filters(body.text)
    except nl.AIUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    results, total = recommend(f)
    if results:
        _save_history(db, user, results)
    return {"results": results, "total_candidates": total, "filters": f}


@app.get("/api/trending", tags=["busca"])
def trending():
    return {"results": tmdb.trending()[:20]}


def _save_history(db: Session, user: User, results: list[dict]) -> None:
    db.add_all(History(
        user_id=user.id, tmdb_id=r["tmdb_id"], content_type=r["content_type"], title=r["title"],
        genres="|".join(r["genres"]), vote_avg=r["vote_avg"], year=r["year"], poster_url=r["poster_url"],
    ) for r in results)
    db.commit()


@app.get("/api/history", tags=["usuário"])
def history(user: User = Depends(auth.current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(History).where(History.user_id == user.id).order_by(History.recommended_at.desc()).limit(30)
    )
    return {"results": [
        {"tmdb_id": h.tmdb_id, "content_type": h.content_type, "title": h.title, "year": h.year,
         "vote_avg": h.vote_avg, "poster_url": h.poster_url, "recommended_at": h.recommended_at.replace(tzinfo=UTC),
         "tmdb_url": f"https://www.themoviedb.org/{h.content_type}/{h.tmdb_id}"}
        for h in rows
    ]}


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
@app.get("/api/admin/summary", tags=["admin"])
def admin_summary(_: User = Depends(auth.admin_user), db: Session = Depends(get_db)):
    genre_count = Counter(g for row in db.scalars(select(History.genres)) for g in row.split("|") if g)
    top_titles = db.execute(
        select(History.title, History.content_type, func.count().label("n"))
        .group_by(History.tmdb_id, History.content_type, History.title)
        .order_by(func.count().desc()).limit(10)
    )
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "recommendations": db.scalar(select(func.count()).select_from(History)),
        "top_genres": [{"name": g, "count": n} for g, n in genre_count.most_common(10)],
        "top_titles": [{"title": t, "content_type": k, "count": n} for t, k, n in top_titles],
    }


@app.get("/api/health", tags=["admin"])
def health():
    return {"status": "ok"}


# O frontend vem por último para não esconder as rotas /api.
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
