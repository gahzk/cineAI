# -*- coding: utf-8 -*-
"""Pydantic schemas for user preferences."""
from typing import List, Optional
from pydantic import BaseModel


class PreferenceUpdate(BaseModel):
    content_type: str = ""            # "movie" | "tv" | ""
    genres_include: List[str] = []
    genres_exclude: List[str] = []
    duration_pref: str = "Qualquer"
    weight_rating: float = 0.8
    weight_popularity: float = 0.8
    prefer_new: bool = False
    classic_focus: bool = False
    keywords: Optional[List[str]] = None
    actor: Optional[str] = None
    director: Optional[str] = None
    company: Optional[str] = None
    network: Optional[str] = None
    year: Optional[int] = None
    min_vote: Optional[float] = None


class PreferenceResponse(PreferenceUpdate):
    id: int
    user_id: int
    model_config = {"from_attributes": True}
