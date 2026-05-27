# -*- coding: utf-8 -*-
"""Pydantic schemas for the analytics dashboard."""
from typing import List
from pydantic import BaseModel


class GenreStat(BaseModel):
    genre: str
    count: int
    percentage: float


class TitleStat(BaseModel):
    tmdb_id: int
    content_type: str
    title: str
    genres: str
    vote_avg: float
    recommendation_count: int
    avg_score: float


class SearchModeStat(BaseModel):
    mode: str
    count: int


class WeightDistribution(BaseModel):
    label: str       # e.g. "Nota Alta (≥0.9)"
    count: int


class AnalyticsSummary(BaseModel):
    total_users: int
    total_recommendations: int
    top_genres: List[GenreStat]
    top_titles: List[TitleStat]
    search_mode_distribution: List[SearchModeStat]
    weight_rating_distribution: List[WeightDistribution]
    insight_most_popular_genre: str
    insight_top_title: str
    insight_search_preference: str
