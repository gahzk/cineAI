# -*- coding: utf-8 -*-
"""Pydantic schemas for recommendation requests and responses."""
from typing import List, Optional
from pydantic import BaseModel


class NormalSearchRequest(BaseModel):
    content_type: str = ""              # "movie" | "tv" | ""
    genres_include: List[str] = []
    genres_exclude: List[str] = []
    duration_pref: str = "Qualquer"
    weight_rating: float = 0.8
    weight_popularity: float = 0.8
    prefer_new: bool = False
    classic_focus: bool = False
    save_preference: bool = True        # persist to DB


class SpecificSearchRequest(NormalSearchRequest):
    keywords: Optional[List[str]] = None
    actor: Optional[str] = None
    director: Optional[str] = None
    company: Optional[str] = None
    network: Optional[str] = None
    year: Optional[int] = None
    min_vote: Optional[float] = None
    rating_br: Optional[str] = None


class CatalogItem(BaseModel):
    tmdb_id: int
    content_type: str
    title: str
    genres: str
    year: Optional[int]
    runtime: Optional[int]
    vote_avg: float
    vote_cnt: int
    popularity: float
    score: float
    rank: int
    synopsis: Optional[str] = None
    director: Optional[str] = None
    cast: Optional[str] = None
    providers: Optional[str] = None
    keywords: Optional[str] = None
    tagline: Optional[str] = None
    rating_br: Optional[str] = None
    companies: Optional[str] = None
    seasons: Optional[int] = None
    episodes: Optional[int] = None
    recommendations: Optional[str] = None
    ai_comment: Optional[str] = None


class SearchResponse(BaseModel):
    mode: str                           # "normal" | "specific"
    total_searched: int
    results: List[CatalogItem]


class CatalogStatusResponse(BaseModel):
    total_items: int
    cache_valid: bool
    message: str
