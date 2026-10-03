"""Cliente do TMDB: uma função de GET, cache em memória e as consultas que o app usa."""
import time
import unicodedata
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import TMDB_TOKEN

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w342"
REGION = "BR"
# Quantas páginas do Discover buscar por tipo (20 títulos cada): o catálogo de cada busca.
DISCOVER_PAGES = 5

# Séries usam gêneros combinados no TMDB. Mapeia o gênero de filme para o de série
# quando o ID não existe nas duas listas (ex.: Ação 28 -> "Action & Adventure" 10759).
MOVIE_TO_TV_GENRE = {28: 10759, 12: 10759, 878: 10765, 14: 10765, 10752: 10768}


class TMDBError(Exception):
    """Falha ao falar com o TMDB; a mensagem já é própria para o usuário."""


_session = requests.Session()
_session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(
        total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"],
    )),
)


def get(path: str, **params: Any) -> dict:
    if not TMDB_TOKEN:
        raise TMDBError("O servidor está sem TMDB_TOKEN. Configure o .env e reinicie.")
    try:
        r = _session.get(
            f"{BASE_URL}{path}",
            params={"language": "pt-BR", **params},
            headers={"Authorization": f"Bearer {TMDB_TOKEN}", "Accept": "application/json"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise TMDBError("Não foi possível falar com o TMDB agora. Tente de novo em instantes.") from exc
    if r.status_code == 401:
        raise TMDBError("O TMDB recusou o token. Confira TMDB_TOKEN no .env.")
    if not r.ok:
        raise TMDBError(f"O TMDB respondeu com erro {r.status_code}. Tente de novo em instantes.")
    return r.json()


_cache: dict[tuple, tuple[float, Any]] = {}


def cached(key: tuple, ttl_s: int, load: Callable[[], Any]) -> Any:
    """Guarda o resultado de `load` por `ttl_s` segundos. Falhas não são guardadas."""
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    value = load()
    _cache[key] = (time.monotonic() + ttl_s, value)
    return value


DAY = 86_400


def genres(kind: str) -> dict[int, str]:
    """{id: nome} dos gêneros de filme ("movie") ou série ("tv")."""
    return cached(("genres", kind), DAY, lambda: {
        g["id"]: g["name"] for g in get(f"/genre/{kind}/list")["genres"]
    })


def genre_ids_for(kind: str, movie_genre_ids: list[int]) -> list[int]:
    """Converte IDs de gênero de filme (o vocabulário do formulário) para o tipo pedido."""
    if kind == "movie":
        return list(dict.fromkeys(movie_genre_ids))
    tv = genres("tv")
    ids = (MOVIE_TO_TV_GENRE.get(g, g) for g in movie_genre_ids)
    return list(dict.fromkeys(g for g in ids if g in tv))


def providers() -> list[dict]:
    """Todos os serviços de streaming do Brasil, em ordem alfabética."""
    def load() -> list[dict]:
        data = get("/watch/providers/movie", watch_region=REGION)["results"]
        items = {p["provider_id"]: p["provider_name"].strip() for p in data}
        return sorted(({"id": i, "name": n} for i, n in items.items()), key=lambda p: sort_key(p["name"]))
    return cached(("providers",), DAY, load)


def sort_key(text: str) -> str:
    """Chave de ordem alfabética que ignora acentos e maiúsculas (Á vem junto com A)."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def first_id(path: str, query: str) -> int | None:
    """ID do primeiro resultado de uma busca do TMDB (pessoa, palavra-chave, produtora)."""
    results = cached(("search", path, query.lower()), DAY, lambda: get(path, query=query)["results"])
    return results[0]["id"] if results else None


def discover(kind: str, params: dict) -> list[dict]:
    """Até DISCOVER_PAGES páginas do Discover (20 títulos cada), sem repetidos, no formato do app."""
    def load() -> list[dict]:
        def page(n: int) -> dict:
            return get(f"/discover/{kind}", include_adult="false", page=n, **params)

        first = page(1)
        last = min(DISCOVER_PAGES, first.get("total_pages") or 1)
        pages = [first]
        if last > 1:
            with ThreadPoolExecutor(max_workers=4) as pool:
                pages += list(pool.map(page, range(2, last + 1)))
        names = genres(kind)
        seen: dict[int, dict] = {}
        for data in pages:
            for raw in data.get("results", []):
                if raw.get("id") not in seen and (item := to_item(raw, kind, names)):
                    seen[raw["id"]] = item
        return list(seen.values())

    items = cached(("discover", kind, tuple(sorted(params.items()))), 3600, load)
    return [dict(item) for item in items]  # cópias: o ranking escreve a nota em cada item


def trending() -> list[dict]:
    def load() -> list[dict]:
        items = []
        for kind in ("movie", "tv"):
            names = genres(kind)
            items += [i for raw in get(f"/trending/{kind}/week")["results"][:10] if (i := to_item(raw, kind, names))]
        return sorted(items, key=lambda i: i["popularity"], reverse=True)
    return cached(("trending",), 3600, load)


def to_item(raw: dict, kind: str, genre_names: dict[int, str]) -> dict | None:
    title = raw.get("title") or raw.get("name") or raw.get("original_title") or raw.get("original_name")
    if not raw.get("id") or not title:
        return None
    date = raw.get("release_date") or raw.get("first_air_date") or ""
    genre_ids = raw.get("genre_ids", [])
    return {
        "tmdb_id": raw["id"],
        "content_type": kind,
        "title": title,
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "genre_ids": genre_ids,
        "genres": [genre_names[g] for g in genre_ids if g in genre_names],
        "vote_avg": float(raw.get("vote_average") or 0),
        "vote_count": int(raw.get("vote_count") or 0),
        "popularity": float(raw.get("popularity") or 0),
        "synopsis": raw.get("overview") or "",
        "poster_url": f"{IMAGE_URL}{raw['poster_path']}" if raw.get("poster_path") else None,
        "tmdb_url": f"https://www.themoviedb.org/{kind}/{raw['id']}",
    }


def add_details(item: dict) -> dict:
    """Completa um item com duração, elenco, onde assistir, classificação e trailer."""
    kind = item["content_type"]
    extra = "credits,watch/providers,videos," + ("release_dates" if kind == "movie" else "content_ratings")
    data = get(f"/{kind}/{item['tmdb_id']}", append_to_response=extra, include_video_language="pt,en")

    if kind == "movie":
        item["runtime"] = data.get("runtime") or None
        people = [c["name"] for c in data.get("credits", {}).get("crew", []) if c.get("job") == "Director"]
    else:
        runtimes = data.get("episode_run_time") or []
        item["runtime"] = round(sum(runtimes) / len(runtimes)) if runtimes else None
        people = [c["name"] for c in data.get("created_by", [])]
        item["seasons"] = data.get("number_of_seasons")
        item["episodes"] = data.get("number_of_episodes")
    item["director"] = ", ".join(people[:2])
    item["cast"] = ", ".join(c["name"] for c in data.get("credits", {}).get("cast", [])[:4])
    item["synopsis"] = data.get("overview") or item.get("synopsis") or ""

    br = data.get("watch/providers", {}).get("results", {}).get(REGION, {})
    item["providers"] = list(dict.fromkeys(p["provider_name"] for p in br.get("flatrate", [])))
    item["rating_br"] = _certification(data, kind)

    videos = data.get("videos", {}).get("results", [])
    trailer = next((v for v in videos if v.get("site") == "YouTube" and v.get("type") == "Trailer"), None)
    item["trailer_url"] = f"https://www.youtube.com/watch?v={trailer['key']}" if trailer else None
    return item


def _certification(data: dict, kind: str) -> str | None:
    if kind == "movie":
        for country in data.get("release_dates", {}).get("results", []):
            if country.get("iso_3166_1") == REGION:
                return next((r["certification"] for r in country["release_dates"] if r.get("certification")), None)
    else:
        for country in data.get("content_ratings", {}).get("results", []):
            if country.get("iso_3166_1") == REGION:
                return country.get("rating") or None
    return None
