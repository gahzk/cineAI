# -*- coding: utf-8 -*-
"""
Analytics service — aggregates RecommendationHistory to power the admin dashboard.

Design principles:
- All heavy queries run async against the DB
- Insights are derived from data (no hard-coded copy)
- Returns plain dicts/Pydantic-ready structures consumed by the router
"""
from collections import Counter, defaultdict
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import RecommendationHistory
from app.models.user import User
from app.models.preference import UserPreference


async def _count_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def _count_recommendations(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(RecommendationHistory))
    return result.scalar_one()


async def get_top_genres(db: AsyncSession, limit: int = 10) -> List[Dict]:
    """Count genre occurrences across all recommendation history entries."""
    result = await db.execute(select(RecommendationHistory.genres))
    rows = result.scalars().all()

    genre_counter: Counter = Counter()
    for genres_str in rows:
        for g in genres_str.split("|"):
            g = g.strip()
            if g:
                genre_counter[g] += 1

    total = sum(genre_counter.values()) or 1
    return [
        {"genre": g, "count": c, "percentage": round(c / total * 100, 1)}
        for g, c in genre_counter.most_common(limit)
    ]


async def get_top_titles(db: AsyncSession, limit: int = 10) -> List[Dict]:
    """Aggregate the most frequently recommended titles with avg score."""
    result = await db.execute(
        select(
            RecommendationHistory.tmdb_id,
            RecommendationHistory.content_type,
            RecommendationHistory.title,
            RecommendationHistory.genres,
            RecommendationHistory.vote_avg,
            func.count(RecommendationHistory.id).label("recommendation_count"),
            func.avg(RecommendationHistory.score).label("avg_score"),
        )
        .group_by(
            RecommendationHistory.tmdb_id,
            RecommendationHistory.content_type,
            RecommendationHistory.title,
            RecommendationHistory.genres,
            RecommendationHistory.vote_avg,
        )
        .order_by(func.count(RecommendationHistory.id).desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "tmdb_id": r.tmdb_id,
            "content_type": r.content_type,
            "title": r.title,
            "genres": r.genres,
            "vote_avg": round(r.vote_avg, 1),
            "recommendation_count": r.recommendation_count,
            "avg_score": round(r.avg_score or 0, 2),
        }
        for r in rows
    ]


async def get_search_mode_distribution(db: AsyncSession) -> List[Dict]:
    result = await db.execute(
        select(
            RecommendationHistory.search_mode,
            func.count(RecommendationHistory.id).label("count"),
        ).group_by(RecommendationHistory.search_mode)
    )
    return [{"mode": r.search_mode, "count": r.count} for r in result.all()]


async def get_weight_rating_distribution(db: AsyncSession) -> List[Dict]:
    """Bucket users' weight_rating preferences into categories."""
    result = await db.execute(select(UserPreference.weight_rating))
    weights = result.scalars().all()

    buckets: Counter = Counter()
    for w in weights:
        if w >= 0.9:
            buckets["Nota Alta (≥0.9)"] += 1
        elif w >= 0.7:
            buckets["Nota Média (0.7–0.9)"] += 1
        else:
            buckets["Popularidade (< 0.7)"] += 1

    return [{"label": k, "count": v} for k, v in buckets.items()]


def _build_insights(top_genres: List[Dict], top_titles: List[Dict], search_modes: List[Dict]) -> Dict[str, str]:
    """Derive natural-language insights from aggregated data."""
    insight_genre = (
        f"O gênero mais recomendado é '{top_genres[0]['genre']}' "
        f"({top_genres[0]['percentage']}% dos resultados). "
        f"Isso indica que a base de usuários tem forte preferência por esse estilo."
        if top_genres else "Ainda sem dados suficientes para analisar gêneros."
    )

    insight_title = (
        f"'{top_titles[0]['title']}' é o título mais recomendado "
        f"({top_titles[0]['recommendation_count']} vezes), "
        f"com nota média de {top_titles[0]['vote_avg']}. "
        f"Alta popularidade combinada com boa avaliação justifica sua presença frequente nos resultados."
        if top_titles else "Sem histórico suficiente para identificar títulos em destaque."
    )

    mode_map = {m["mode"]: m["count"] for m in search_modes}
    normal = mode_map.get("normal", 0)
    specific = mode_map.get("specific", 0)
    total_modes = normal + specific or 1
    dominant = "Busca Normal" if normal >= specific else "Busca Específica"
    insight_search = (
        f"A {dominant} é o modo preferido dos usuários "
        f"({round(max(normal, specific) / total_modes * 100)}% das buscas). "
        + ("Usuários preferem descobertas rápidas pelo catálogo local."
           if dominant == "Busca Normal"
           else "Usuários fazem buscas detalhadas com filtros avançados (ator, diretor, streaming).")
    )

    return {
        "insight_most_popular_genre": insight_genre,
        "insight_top_title": insight_title,
        "insight_search_preference": insight_search,
    }


async def get_summary(db: AsyncSession) -> Dict[str, Any]:
    """Aggregate all analytics into a single summary dict for the dashboard."""
    total_users = await _count_users(db)
    total_recs = await _count_recommendations(db)
    top_genres = await get_top_genres(db)
    top_titles = await get_top_titles(db)
    search_modes = await get_search_mode_distribution(db)
    weight_dist = await get_weight_rating_distribution(db)
    insights = _build_insights(top_genres, top_titles, search_modes)

    return {
        "total_users": total_users,
        "total_recommendations": total_recs,
        "top_genres": top_genres,
        "top_titles": top_titles,
        "search_mode_distribution": search_modes,
        "weight_rating_distribution": weight_dist,
        **insights,
    }
