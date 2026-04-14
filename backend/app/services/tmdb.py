# -*- coding: utf-8 -*-
"""
TMDB API service — extracted and refactored from the CineAI legacy notebook.

Key improvements over the notebook version:
- Stateless service class (no globals)
- Uses app.config.settings for all configuration
- JSON cache replaced with filesystem cache (Redis-ready interface)
- All side-effects (Rich progress bars) removed; pure data layer
"""
import json
import logging
import os
import random
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import concurrent.futures as cf
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.core.utils import get_year, safe_float, safe_int

log = logging.getLogger("cineai.tmdb")

# ---------------------------------------------------------------------------
# HTTP session (singleton per process)
# ---------------------------------------------------------------------------

_SESSION: Optional[requests.Session] = None
_SESSION_LOCK = threading.Lock()


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        with _SESSION_LOCK:
            if _SESSION is None:
                session = requests.Session()
                retry = Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504],
                    allowed_methods=["GET"],
                )
                adapter = HTTPAdapter(
                    max_retries=retry,
                    pool_connections=settings.HTTP_WORKERS,
                    pool_maxsize=settings.HTTP_WORKERS,
                )
                session.mount("https://", adapter)
                session.headers.update({
                    "Authorization": f"Bearer {settings.TMDB_BEARER_TOKEN}",
                    "Accept": "application/json",
                })
                _SESSION = session
    return _SESSION


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

_rate_lock = threading.Lock()
_last_request_time: float = 0.0


def _rate_limited_wait() -> None:
    global _last_request_time
    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < settings.MIN_REQUEST_INTERVAL:
            time.sleep(settings.MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# Core request helper
# ---------------------------------------------------------------------------

def tmdb_request(path: str, params: Optional[Dict] = None, retries: int = 3) -> Dict:
    """Execute a GET request against the TMDB API with retry/back-off."""
    wait_time = 0.3
    params = params or {}
    session = _get_session()

    for attempt in range(retries + 1):
        _rate_limited_wait()
        try:
            r = session.get(
                f"{settings.TMDB_BASE_URL}{path}", params=params, timeout=20
            )
            if r.status_code == 429:
                retry_after = safe_float(r.headers.get("Retry-After"), wait_time)
                time.sleep(min(10.0, retry_after))
                wait_time = min(5.0, wait_time * 2)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if attempt < retries:
                time.sleep(wait_time + random.uniform(0, wait_time * 0.3))
                wait_time = min(5.0, wait_time * 2)
            else:
                log.warning("Failed after %d attempts on %s: %s", retries + 1, path, exc)
    return {}


# ---------------------------------------------------------------------------
# File-based cache (JSON, swap-safe atomic writes)
# ---------------------------------------------------------------------------

GENRES_CACHE = settings.CACHE_DIR / "genres.json"
CATALOG_CACHE = settings.CACHE_DIR / "catalog.json"


def _read_cache(filepath: Path) -> Optional[Any]:
    try:
        age_days = (time.time() - filepath.stat().st_mtime) / 86400
        if age_days > settings.CACHE_EXPIRATION_DAYS:
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Corrupt cache at %s: %s", filepath, exc)
        return None


def _write_cache(filepath: Path, data: Any) -> None:
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(filepath.parent), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(filepath))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as exc:
        log.warning("Failed to write cache %s: %s", filepath, exc)


# ---------------------------------------------------------------------------
# Genres
# ---------------------------------------------------------------------------

_genres_cache: Optional[Dict] = None


def get_genres() -> Dict[str, Dict[str, str]]:
    """Return {movie_genres: {id: name}, tv_genres: {id: name}}, with cache."""
    global _genres_cache
    if _genres_cache:
        return _genres_cache
    cached = _read_cache(GENRES_CACHE)
    if cached and "movie_genres" in cached and "tv_genres" in cached:
        _genres_cache = cached
        return _genres_cache

    mg = tmdb_request("/genre/movie/list", {"language": "pt-BR"}).get("genres", [])
    tg = tmdb_request("/genre/tv/list", {"language": "pt-BR"}).get("genres", [])
    genres = {
        "movie_genres": {str(g["id"]): g["name"] for g in mg if "id" in g and "name" in g},
        "tv_genres": {str(g["id"]): g["name"] for g in tg if "id" in g and "name" in g},
    }
    _write_cache(GENRES_CACHE, genres)
    _genres_cache = genres
    return genres


# ---------------------------------------------------------------------------
# Catalog item builder
# ---------------------------------------------------------------------------

def build_catalog_item(it: Dict, kind: str, g_map: Dict[str, str]) -> Optional[Dict]:
    item_id = it.get("id")
    if not item_id:
        return None
    tk = "title" if kind == "movie" else "name"
    otk = "original_title" if kind == "movie" else "original_name"
    dk = "release_date" if kind == "movie" else "first_air_date"
    title = it.get(tk) or it.get(otk) or ""
    if not title:
        return None
    g_list = [g_map[str(gid)] for gid in it.get("genre_ids", []) if str(gid) in g_map]
    return {
        "id": item_id,
        "type": kind,
        "title": title,
        "genres": "|".join(g_list),
        "year": get_year(it.get(dk)),
        "runtime": None,
        "vote_avg": safe_float(it.get("vote_average")),
        "vote_cnt": safe_int(it.get("vote_count")),
        "popularity": safe_float(it.get("popularity")),
    }


# ---------------------------------------------------------------------------
# Live catalog fetch (threaded discover)
# ---------------------------------------------------------------------------

def _discover_page(task: tuple) -> Tuple[List[Dict], bool]:
    kind, _g, sort_by, _date_range, page, lang, all_g, keywords = task
    params: Dict[str, Any] = {
        "language": lang,
        "sort_by": sort_by,
        "page": page,
        "include_adult": "false",
        "vote_count.gte": 100,
    }
    if keywords:
        params["with_keywords"] = keywords
    data = tmdb_request(f"/discover/{kind}", params)
    g_map = all_g["movie_genres"] if kind == "movie" else all_g["tv_genres"]
    results = [
        item
        for it in data.get("results", [])
        if (item := build_catalog_item(it, kind, g_map))
    ]
    return results, data.get("page", 0) < data.get("total_pages", 0)


def fetch_live_catalog(target: int, lang: str = "pt-BR") -> List[Dict]:
    """Fetch up to `target` titles from the TMDB Discover API concurrently."""
    g = get_genres()
    m_ids_map = {name: gid for gid, name in g["movie_genres"].items()}
    t_ids_map = {name: gid for gid, name in g["tv_genres"].items()}
    m_ids = list(m_ids_map.values())
    t_ids = list(t_ids_map.values())

    series_tasks: List[tuple] = []
    anime_keyword = "210024"
    anime_genres = [t_ids_map[gn] for gn in ["Animação", "Ação e Aventura", "Sci-Fi & Fantasy"] if gn in t_ids_map]
    if anime_genres:
        for sort_key in ["popularity.desc", "vote_average.desc"]:
            for page in range(1, 11):
                series_tasks.append(("tv", anime_genres, sort_key, ("2000-01-01", "2025-12-31"), page, lang, g, anime_keyword))
    for sort_key in ["popularity.desc", "vote_average.desc"]:
        for chunk in [t_ids[i:i+2] for i in range(0, len(t_ids), 2)]:
            for page in range(1, 4):
                series_tasks.append(("tv", chunk, sort_key, ("2010-01-01", "2025-12-31"), page, lang, g, None))

    general_tasks: List[tuple] = []
    decades = [("1990-01-01","1999-12-31"),("2000-01-01","2009-12-31"),("2010-01-01","2019-12-31"),("2020-01-01","2025-12-31")]
    for d in decades:
        for s_ in ["vote_average.desc", "popularity.desc"]:
            for chunk in [random.sample(m_ids, len(m_ids))[i:i+2] for i in range(0, len(m_ids), 2)]:
                general_tasks.append(("movie", chunk, s_, d, 1, lang, g, None))
            for chunk in [random.sample(t_ids, len(t_ids))[i:i+2] for i in range(0, len(t_ids), 2)]:
                general_tasks.append(("tv", chunk, s_, d, 1, lang, g, None))

    random.shuffle(series_tasks)
    random.shuffle(general_tasks)
    tasks: deque = deque(series_tasks + general_tasks)
    catalog: List[Dict] = []
    seen_ids: set = set()
    workers = settings.HTTP_WORKERS

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures: Dict[cf.Future, tuple] = {}
        for _ in range(min(len(tasks), workers * 2)):
            if tasks:
                t = tasks.popleft()
                futures[ex.submit(_discover_page, t)] = t
        while futures and len(catalog) < target:
            done, _ = cf.wait(futures, return_when=cf.FIRST_COMPLETED)
            for fut in done:
                orig_task = futures.pop(fut)
                try:
                    batch, has_more = fut.result()
                    for item in batch:
                        key = (item["type"], item["id"])
                        if key not in seen_ids:
                            seen_ids.add(key)
                            catalog.append(item)
                    kind, gn, s_, d, p, ln, gs, kw = orig_task
                    if has_more and p < 15 and len(catalog) < target:
                        tasks.append((kind, gn, s_, d, p + 1, ln, gs, kw))
                except Exception as exc:
                    log.debug("Page processing error: %s", exc)
                if tasks and len(futures) < workers * 2:
                    t = tasks.popleft()
                    futures[ex.submit(_discover_page, t)] = t

    return catalog[:target]


def get_catalog(force_rebuild: bool = False) -> List[Dict]:
    """Return the catalog from cache or rebuild it from TMDB."""
    if not force_rebuild:
        cached = _read_cache(CATALOG_CACHE)
        if cached and isinstance(cached, list) and len(cached) > 0:
            return cached
    catalog = fetch_live_catalog(settings.CATALOG_TARGET)
    _write_cache(CATALOG_CACHE, catalog)
    return catalog


def catalog_status() -> Dict:
    cached = _read_cache(CATALOG_CACHE)
    if cached and isinstance(cached, list):
        return {"total_items": len(cached), "cache_valid": True, "message": f"Catálogo pronto com {len(cached)} títulos."}
    return {"total_items": 0, "cache_valid": False, "message": "Cache inválido ou expirado."}


# ---------------------------------------------------------------------------
# Discover-on-the-fly (specific search)
# ---------------------------------------------------------------------------

def _get_search_id(name: str, path: str) -> Optional[str]:
    from app.core.utils import is_empty
    if is_empty(name):
        return None
    data = tmdb_request(path, {"language": "pt-BR", "query": name})
    results = data.get("results", [])
    if results:
        return str(results[0]["id"])
    return None


def _get_keyword_ids(terms: List[str]) -> Optional[str]:
    from app.core.utils import is_empty
    ids = []
    for term in terms:
        if is_empty(term):
            continue
        data = tmdb_request("/search/keyword", {"query": term})
        results = data.get("results", [])
        if results:
            ids.append(str(results[0]["id"]))
    return ",".join(ids) if ids else None


def build_discover_params(prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Build TMDB /discover query params from a preference dict."""
    from app.core.utils import is_empty
    g = get_genres()
    m_ids_map = {name: gid for gid, name in g["movie_genres"].items()}
    t_ids_map = {name: gid for gid, name in g["tv_genres"].items()}

    inc_ids_m = [str(m_ids_map[n]) for n in prefs.get("inc", []) if n in m_ids_map]
    inc_ids_t = [str(t_ids_map[n]) for n in prefs.get("inc", []) if n in t_ids_map]
    exc_ids_m = [str(m_ids_map[n]) for n in prefs.get("exc", []) if n in m_ids_map]
    exc_ids_t = [str(t_ids_map[n]) for n in prefs.get("exc", []) if n in t_ids_map]

    ctype = prefs.get("type", "")
    if ctype == "movie":
        inc_g, exc_g = inc_ids_m, exc_ids_m
    elif ctype == "tv":
        inc_g, exc_g = inc_ids_t, exc_ids_t
    else:
        inc_g = list(set(inc_ids_m + inc_ids_t))
        exc_g = list(set(exc_ids_m + exc_ids_t))

    params: Dict[str, Any] = {
        "language": "pt-BR",
        "include_adult": "false",
        "vote_count.gte": 150,
    }
    if inc_g:
        params["with_genres"] = ",".join(inc_g)
    if exc_g:
        params["without_genres"] = ",".join(exc_g)

    if prefs.get("keywords_raw"):
        kw_ids = _get_keyword_ids(prefs["keywords_raw"])
        if kw_ids:
            params["with_keywords"] = kw_ids
    if prefs.get("actor_raw") and not is_empty(prefs["actor_raw"]):
        pid = _get_search_id(prefs["actor_raw"], "/search/person")
        if pid:
            params["with_cast"] = pid
    if prefs.get("director_raw") and not is_empty(prefs["director_raw"]):
        pid = _get_search_id(prefs["director_raw"], "/search/person")
        if pid:
            params["with_crew"] = pid
    if prefs.get("company_raw") and not is_empty(prefs["company_raw"]):
        cid = _get_search_id(prefs["company_raw"], "/search/company")
        if cid:
            params["with_companies"] = cid
    if prefs.get("network_raw") and not is_empty(prefs["network_raw"]):
        nid = _get_search_id(prefs["network_raw"], "/search/network")
        if nid:
            params["with_networks"] = nid
    if prefs.get("year_raw"):
        key = "primary_release_year" if ctype != "tv" else "first_air_date_year"
        params[key] = prefs["year_raw"]
    if prefs.get("min_vote_raw"):
        params["vote_average.gte"] = prefs["min_vote_raw"]
    if prefs.get("rating_raw") and prefs["rating_raw"] != "NENHUM":
        params["certification_country"] = "BR"
        params["certification.lte"] = prefs["rating_raw"]

    if "primary_release_year" not in params and "first_air_date_year" not in params:
        if prefs.get("classic_focus"):
            dk = "primary_release_date.lte" if ctype != "tv" else "first_air_date.lte"
            params[dk] = "2000-01-01"
            params["sort_by"] = "vote_average.desc"
        elif prefs.get("prefer_new"):
            dk = "primary_release_date.gte" if ctype != "tv" else "first_air_date.gte"
            params[dk] = "2010-01-01"
            params["sort_by"] = "popularity.desc"
    if "sort_by" not in params:
        params["sort_by"] = (
            "vote_average.desc" if prefs.get("w_rating", 0.8) > prefs.get("w_pop", 0.8)
            else "popularity.desc"
        )
    return params


def fetch_live_discover(kind: str, params: Dict[str, Any], target_pages: int = 3) -> List[Dict]:
    """Fetch pages from /discover/{kind} with the given params."""
    g_map = get_genres()["movie_genres"] if kind == "movie" else get_genres()["tv_genres"]
    catalog: List[Dict] = []
    seen_ids: set = set()
    for p in range(1, target_pages + 1):
        params["page"] = p
        data = tmdb_request(f"/discover/{kind}", params)
        results = data.get("results", [])
        if not results:
            break
        for it in results:
            item = build_catalog_item(it, kind, g_map)
            if item:
                key = (kind, item["id"])
                if key not in seen_ids:
                    seen_ids.add(key)
                    catalog.append(item)
    return catalog


# ---------------------------------------------------------------------------
# Detail enrichment
# ---------------------------------------------------------------------------

def _parse_certification(data: Dict, kind: str) -> str:
    try:
        if kind == "movie":
            for r in data.get("release_dates", {}).get("results", []):
                if r.get("iso_3166_1") == "BR":
                    for cert in r.get("release_dates", []):
                        if c := cert.get("certification"):
                            return c
        else:
            for r in data.get("content_ratings", {}).get("results", []):
                if r.get("iso_3166_1") == "BR":
                    return r.get("rating", "N/A")
    except (KeyError, TypeError):
        pass
    return "N/A"


def fetch_details(item: Dict) -> Dict:
    """Enrich a catalog item dict with full TMDB details (in-place + return)."""
    kind = item["type"]
    ap = "credits,watch/providers,keywords,recommendations"
    ap += ",release_dates" if kind == "movie" else ",content_ratings"
    data = tmdb_request(f"/{kind}/{item['id']}", {"language": "pt-BR", "append_to_response": ap})
    if not data:
        return item

    if kind == "movie":
        item["runtime"] = safe_int(data.get("runtime")) or None
    else:
        ep_rt = data.get("episode_run_time", [])
        item["runtime"] = int(sum(ep_rt) / len(ep_rt)) if ep_rt else None

    item["synopsis"] = data.get("overview") or "Sinopse não disponível."

    if kind == "movie":
        dirs = [c["name"] for c in data.get("credits", {}).get("crew", []) if c.get("job") == "Director"]
        item["director"] = ", ".join(dirs[:2]) if dirs else "N/A"
    else:
        creators = [c["name"] for c in data.get("created_by", [])]
        item["director"] = ", ".join(creators[:2]) if creators else "N/A"

    cast = [c["name"] for c in data.get("credits", {}).get("cast", [])[:4]]
    item["cast"] = ", ".join(cast) if cast else "N/A"

    prov_data = data.get("watch/providers", {}).get("results", {}).get("BR", {})
    streaming = [p["provider_name"] for p in prov_data.get("flatrate", [])]
    item["providers"] = ", ".join(list(dict.fromkeys(streaming))) if streaming else "Não disponível em streaming"

    kw_data = data.get("keywords", {})
    kw_list = kw_data.get("keywords", kw_data.get("results", []))
    item["keywords"] = ", ".join([k["name"] for k in kw_list[:5]]) if kw_list else "N/A"

    rec_data = data.get("recommendations", {}).get("results", [])
    rn = [r.get("title") or r.get("name") for r in rec_data[:3] if r.get("title") or r.get("name")]
    item["recommendations"] = ", ".join(rn) if rn else "Nenhuma recomendação similar."

    item["tagline"] = data.get("tagline") or ""
    item["rating_br"] = _parse_certification(data, kind)
    item["companies"] = ", ".join([c["name"] for c in data.get("production_companies", [])[:2]])
    if kind == "tv":
        item["seasons"] = data.get("number_of_seasons")
        item["episodes"] = data.get("number_of_episodes")
    return item


def fetch_details_concurrent(items: List[Dict]) -> List[Dict]:
    """Enrich a list of catalog items concurrently."""
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        return list(ex.map(fetch_details, items))
