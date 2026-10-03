"""A recomendação: filtros do usuário -> candidatos do TMDB -> nota -> top 3 com o porquê."""
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel, Field

from app import tmdb

TOP_N = 3

Kind = Literal["", "movie", "tv"]
Era = Literal["any", "new", "classic"]
Order = Literal["balanced", "rating", "popularity"]
Duration = Literal["any", "short", "medium", "long"]

# Pesos de cada ordenação: (nota, popularidade). "balanced" é o padrão.
ORDER_WEIGHTS = {"balanced": (0.8, 0.8), "rating": (1.0, 0.3), "popularity": (0.3, 1.0)}
# Duração em minutos (só filmes; o TMDB não filtra série por duração de forma útil).
DURATIONS = {"short": (None, 100), "medium": (90, 140), "long": (140, None)}
GENRE_POINTS = 15


class Filters(BaseModel):
    """O formulário de busca. Gêneros usam os IDs de filme do TMDB como vocabulário."""

    content_type: Kind = ""
    genres: list[int] = Field(default=[], max_length=10)
    exclude_genres: list[int] = Field(default=[], max_length=10)
    era: Era = "any"
    order: Order = "balanced"
    duration: Duration = "any"
    keyword: str = Field(default="", max_length=100)
    actor: str = Field(default="", max_length=100)
    director: str = Field(default="", max_length=100)
    year: int | None = Field(default=None, ge=1888, le=2100)
    min_vote: float | None = Field(default=None, ge=0, le=10)
    provider: int | None = None
    rating_br: Literal["", "L", "10", "12", "14", "16", "18"] = ""


def kinds_for(f: Filters) -> list[str]:
    """Ator e diretor só existem no Discover de filmes, então a busca vira só de filmes."""
    if f.content_type:
        return [f.content_type]
    return ["movie"] if (f.actor or f.director) else ["movie", "tv"]


def discover_params(kind: str, f: Filters) -> dict | None:
    """Parâmetros do /discover. None quando o tipo não tem nenhum dos gêneros pedidos."""
    include = tmdb.genre_ids_for(kind, f.genres)
    if f.genres and not include:
        return None
    exclude = tmdb.genre_ids_for(kind, f.exclude_genres)
    is_movie = kind == "movie"
    date = "primary_release_date" if is_movie else "first_air_date"

    p: dict = {
        "sort_by": "vote_average.desc" if f.order == "rating" else "popularity.desc",
        "vote_count.gte": 300 if f.order == "rating" else 100,
    }
    if include:
        p["with_genres"] = "|".join(map(str, include))  # | = OU; vírgula seria E
    if exclude:
        p["without_genres"] = "|".join(map(str, exclude))
    if f.year:
        p["primary_release_year" if is_movie else "first_air_date_year"] = f.year
    elif f.era == "new":
        p[f"{date}.gte"] = "2010-01-01"
    elif f.era == "classic":
        p[f"{date}.lte"] = "1999-12-31"
    if f.min_vote is not None:
        p["vote_average.gte"] = f.min_vote
    if f.provider:
        p["with_watch_providers"] = f.provider
        p["watch_region"] = tmdb.REGION
    if f.keyword and (kid := tmdb.first_id("/search/keyword", f.keyword)):
        p["with_keywords"] = kid
    if is_movie:
        low, high = DURATIONS.get(f.duration, (None, None))
        if low:
            p["with_runtime.gte"] = low
        if high:
            p["with_runtime.lte"] = high
        if f.actor and (pid := tmdb.first_id("/search/person", f.actor)):
            p["with_cast"] = pid
        if f.director and (pid := tmdb.first_id("/search/person", f.director)):
            p["with_crew"] = pid
        if f.rating_br:
            p["certification_country"] = tmdb.REGION
            p["certification.lte"] = f.rating_br
    return p


def score(item: dict, f: Filters) -> float:
    """Nota de 0 a ~60. Cada parcela aparece em `reasons` para o usuário ver o porquê."""
    w_rating, w_pop = ORDER_WEIGHTS[f.order]
    wanted = set(tmdb.genre_ids_for(item["content_type"], f.genres))
    s = GENRE_POINTS * len(wanted & set(item["genre_ids"]))
    quality = item["vote_avg"] / 10 * min(1.0, item["vote_count"] / 5000)
    s += 12 * w_rating * quality
    s += 12 * w_pop * min(1.0, item["popularity"] / 300)
    year = item["year"] or 2000
    if f.era == "classic":
        s += max(0, (2000 - year) / 10)
    elif f.era == "new":
        s += max(0, (year - 2010) / 3)
    return round(s, 2)


def reasons(item: dict, f: Filters) -> list[str]:
    out = []
    wanted = set(tmdb.genre_ids_for(item["content_type"], f.genres))
    names = tmdb.genres(item["content_type"])
    matched = [names[g] for g in item["genre_ids"] if g in wanted and g in names]
    if matched:
        out.append(f"Tem o que você pediu: {', '.join(matched)}.")
    if item["vote_avg"] >= 7.5 and item["vote_count"] >= 1000:
        votos = f"{item['vote_count']:,}".replace(",", ".")
        out.append(f"Muito bem avaliado: nota {item['vote_avg']:.1f} com {votos} votos.")
    if item["popularity"] >= 100:
        out.append("Está entre os mais procurados no TMDB agora.")
    if f.era == "classic" and item["year"] and item["year"] < 2000:
        out.append(f"Clássico de {item['year']}.")
    if f.era == "new" and item["year"] and item["year"] >= 2010:
        out.append(f"Lançamento recente ({item['year']}).")
    if f.actor and item["content_type"] == "movie":
        out.append(f"Com {f.actor}.")
    if f.director and item["content_type"] == "movie":
        out.append(f"Direção de {f.director}.")
    if item.get("providers"):
        out.append(f"Disponível em {', '.join(item['providers'][:3])}.")
    return out or ["Combina com os filtros que você escolheu."]


def recommend(f: Filters) -> tuple[list[dict], int]:
    """Top 3 já com detalhes e motivos, e quantos candidatos foram avaliados."""
    candidates: list[dict] = []
    for kind in kinds_for(f):
        params = discover_params(kind, f)
        if params is not None:
            candidates += tmdb.discover(kind, params)
    for item in candidates:
        item["score"] = score(item, f)
    top = sorted(candidates, key=lambda i: i["score"], reverse=True)[:TOP_N]
    with ThreadPoolExecutor(max_workers=TOP_N) as pool:
        top = list(pool.map(tmdb.add_details, top))
    for item in top:
        item["reasons"] = reasons(item, f)
    return top, len(candidates)
