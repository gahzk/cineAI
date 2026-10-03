"""Ambiente de teste: SQLite temporário e um TMDB falso, sem rede."""
import os
import tempfile

os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789"
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["TMDB_TOKEN"] = "fake"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, tmdb  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

MOVIE_GENRES = {28: "Ação", 18: "Drama", 80: "Crime", 27: "Terror", 35: "Comédia", 878: "Ficção científica"}
TV_GENRES = {10759: "Action & Adventure", 18: "Drama", 80: "Crime", 35: "Comédia", 10765: "Sci-Fi & Fantasy"}


def raw(id_, title, genre_ids, vote=7.0, votes=2000, pop=50.0, date="2015-05-01", tv=False):
    key, date_key = ("name", "first_air_date") if tv else ("title", "release_date")
    return {"id": id_, key: title, "genre_ids": genre_ids, "vote_average": vote, "vote_count": votes,
            "popularity": pop, date_key: date, "overview": f"Sinopse de {title}", "poster_path": f"/{id_}.jpg"}


MOVIES = [
    raw(1, "Drama Popular", [18], vote=6.5, votes=800, pop=250),
    raw(2, "Crime Aclamado", [80, 18], vote=8.6, votes=20000, pop=90),
    raw(3, "Ação Recente", [28], vote=7.2, votes=4000, pop=120, date="2023-02-01"),
    raw(4, "Clássico de Crime", [80], vote=8.4, votes=9000, pop=40, date="1974-12-20"),
]
SERIES = [raw(101, "Série de Crime", [80, 18], vote=8.8, votes=12000, pop=150, tv=True)]


class FakeTMDB:
    """Responde às rotas do TMDB que o app usa e guarda cada chamada em `calls`."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.fail = False

    def __call__(self, path: str, **params):
        self.calls.append((path, params))
        if self.fail:
            raise tmdb.TMDBError("Não foi possível falar com o TMDB agora. Tente de novo em instantes.")
        if path == "/genre/movie/list":
            return {"genres": [{"id": k, "name": v} for k, v in MOVIE_GENRES.items()]}
        if path == "/genre/tv/list":
            return {"genres": [{"id": k, "name": v} for k, v in TV_GENRES.items()]}
        if path == "/watch/providers/movie":
            return {"results": [{"provider_id": 8, "provider_name": "Netflix", "display_priorities": {"BR": 1}}]}
        if path.startswith("/search/"):
            return {"results": [{"id": 500}]}
        if path.startswith("/discover/movie"):
            return {"results": MOVIES}
        if path.startswith("/discover/tv"):
            return {"results": SERIES}
        if path.startswith("/trending/movie"):
            return {"results": MOVIES}
        if path.startswith("/trending/tv"):
            return {"results": SERIES}
        if path.startswith(("/movie/", "/tv/")):
            return {
                "runtime": 120, "credits": {"crew": [{"job": "Director", "name": "Diretora X"}],
                                            "cast": [{"name": "Atriz Y"}]},
                "watch/providers": {"results": {"BR": {"flatrate": [{"provider_name": "Netflix"}]}}},
                "videos": {"results": [{"site": "YouTube", "type": "Trailer", "key": "abc"}]},
                "release_dates": {"results": [{"iso_3166_1": "BR", "release_dates": [{"certification": "14"}]}]},
            }
        raise AssertionError(f"rota TMDB inesperada: {path}")


@pytest.fixture
def fake_tmdb(monkeypatch):
    fake = FakeTMDB()
    monkeypatch.setattr(tmdb, "get", fake)
    tmdb._cache.clear()
    return fake


@pytest.fixture
def client(fake_tmdb):
    Base.metadata.drop_all(engine)
    auth._attempts.clear()
    with TestClient(app) as c:
        yield c


ANA = {"email": "ana@exemplo.com", "username": "ana", "password": "senha-forte"}


@pytest.fixture
def token(client):
    r = client.post("/api/auth/register", json=ANA)
    return r.json()["access_token"]
