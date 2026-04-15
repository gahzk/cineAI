# -*- coding: utf-8 -*-
"""Recommendations router — normal search, specific search, catalog status."""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import normalize
from app.database import get_db
from app.models.history import RecommendationHistory
from app.models.preference import UserPreference
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.recommendation import (
    CatalogItem,
    CatalogStatusResponse,
    NormalSearchRequest,
    SearchResponse,
    SpecificSearchRequest,
)
from app.services import scoring, tmdb

log = logging.getLogger("cineai.recs")
router = APIRouter(prefix="/recommendations", tags=["recommendations"])

TOP_N = 3  # How many results to enrich and return


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prefs_from_normal(body: NormalSearchRequest) -> Dict[str, Any]:
    inc_genres = scoring.map_terms_to_genres(body.genres_include) if body.genres_include else body.genres_include
    exc_genres = scoring.map_terms_to_genres(body.genres_exclude) if body.genres_exclude else body.genres_exclude
    return {
        "type": body.content_type,
        "inc": inc_genres,
        "exc": exc_genres,
        "inc_norm": [normalize(g) for g in inc_genres],
        "exc_norm": [normalize(g) for g in exc_genres],
        "dur": body.duration_pref,
        "prefer_new": body.prefer_new,
        "classic_focus": body.classic_focus,
        "w_rating": body.weight_rating,
        "w_pop": body.weight_popularity,
    }


def _prefs_from_specific(body: SpecificSearchRequest) -> Dict[str, Any]:
    base = _prefs_from_normal(body)
    base.update({
        "keywords_raw": body.keywords or [],
        "actor_raw": body.actor or "",
        "director_raw": body.director or "",
        "company_raw": body.company or "",
        "network_raw": body.network or "",
        "year_raw": str(body.year) if body.year else "",
        "min_vote_raw": str(body.min_vote) if body.min_vote else "",
        "rating_raw": body.rating_br or "NENHUM",
    })
    return base


def _catalog_item_to_schema(item: Dict, rank: int, score: float) -> CatalogItem:
    return CatalogItem(
        tmdb_id=item["id"],
        content_type=item["type"],
        title=item["title"],
        genres=item.get("genres", ""),
        year=item.get("year"),
        runtime=item.get("runtime"),
        vote_avg=item.get("vote_avg", 0.0),
        vote_cnt=item.get("vote_cnt", 0),
        popularity=item.get("popularity", 0.0),
        score=round(score, 2),
        rank=rank,
        synopsis=item.get("synopsis"),
        director=item.get("director"),
        cast=item.get("cast"),
        providers=item.get("providers"),
        keywords=item.get("keywords"),
        tagline=item.get("tagline"),
        rating_br=item.get("rating_br"),
        companies=item.get("companies"),
        seasons=item.get("seasons"),
        episodes=item.get("episodes"),
        recommendations=item.get("recommendations"),
        ai_comment=item.get("ai_comment"),
    )


async def _save_history(
    db: AsyncSession,
    user: User,
    results: List[CatalogItem],
    search_mode: str,
    prefs: Dict,
) -> None:
    """Persist recommendation events and upsert user preference."""
    for r in results:
        db.add(RecommendationHistory(
            user_id=user.id,
            tmdb_id=r.tmdb_id,
            content_type=r.content_type,
            title=r.title,
            genres=r.genres,
            vote_avg=r.vote_avg,
            popularity=r.popularity,
            year=r.year,
            score=r.score,
            rank=r.rank,
            search_mode=search_mode,
        ))

    # Upsert last preference
    from sqlalchemy import select
    existing = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id).limit(1)
    )
    pref_row = existing.scalar_one_or_none()
    if pref_row is None:
        pref_row = UserPreference(user_id=user.id)
        db.add(pref_row)

    pref_row.content_type = prefs.get("type", "")
    pref_row.genres_include = "|".join(prefs.get("inc", []))
    pref_row.genres_exclude = "|".join(prefs.get("exc", []))
    pref_row.duration_pref = prefs.get("dur", "Qualquer")
    pref_row.weight_rating = prefs.get("w_rating", 0.8)
    pref_row.weight_popularity = prefs.get("w_pop", 0.8)
    pref_row.prefer_new = prefs.get("prefer_new", False)
    pref_row.classic_focus = prefs.get("classic_focus", False)

    await db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/catalog/status", response_model=CatalogStatusResponse)
async def catalog_status():
    status = tmdb.catalog_status()
    return CatalogStatusResponse(**status)


@router.post("/search", response_model=SearchResponse)
async def normal_search(
    body: NormalSearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Score the local catalog against the user's preferences and return top 3."""
    catalog = tmdb.get_catalog()
    if not catalog:
        raise HTTPException(status_code=503, detail="Catálogo não disponível. Tente novamente em alguns minutos.")

    prefs = _prefs_from_normal(body)
    scored = sorted(
        [(scoring.score_item(item, prefs), item) for item in catalog],
        key=lambda x: x[0],
        reverse=True,
    )

    top_items = [item for _, item in scored[:TOP_N]]
    top_scores = [s for s, _ in scored[:TOP_N]]

    # Enrich with TMDB details
    enriched = tmdb.fetch_details_concurrent(top_items)
    for item in enriched:
        item["ai_comment"] = scoring.generate_ai_comment(item)

    results = [
        _catalog_item_to_schema(item, rank=i + 1, score=top_scores[i])
        for i, item in enumerate(enriched)
    ]

    if body.save_preference:
        background_tasks.add_task(_save_history, db, current_user, results, "normal", prefs)

    return SearchResponse(mode="normal", total_searched=len(catalog), results=results)


@router.post("/search/specific", response_model=SearchResponse)
async def specific_search(
    body: SpecificSearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch directly from TMDB Discover with the user's specific filters, return top 3."""
    prefs = _prefs_from_specific(body)
    api_params = tmdb.build_discover_params(prefs)
    ctype = body.content_type

    live_catalog: List[Dict] = []
    if ctype == "movie":
        live_catalog = tmdb.fetch_live_discover("movie", api_params.copy())
    elif ctype == "tv":
        live_catalog = tmdb.fetch_live_discover("tv", api_params.copy())
    else:
        live_catalog.extend(tmdb.fetch_live_discover("movie", api_params.copy(), target_pages=2))
        live_catalog.extend(tmdb.fetch_live_discover("tv", api_params.copy(), target_pages=2))

    if not live_catalog:
        raise HTTPException(status_code=404, detail="Nenhum resultado encontrado para esses filtros.")

    top_items = live_catalog[:TOP_N]
    enriched = tmdb.fetch_details_concurrent(top_items)
    for item in enriched:
        item["ai_comment"] = scoring.generate_ai_comment(item)

    results = [
        _catalog_item_to_schema(item, rank=i + 1, score=float(len(live_catalog) - i))
        for i, item in enumerate(enriched)
    ]

    background_tasks.add_task(_save_history, db, current_user, results, "specific", prefs)

    return SearchResponse(mode="specific", total_searched=len(live_catalog), results=results)
