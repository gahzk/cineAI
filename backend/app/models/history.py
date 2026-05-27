# -*- coding: utf-8 -*-
"""RecommendationHistory ORM model — audit log of every result shown to a user."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class RecommendationHistory(Base):
    """One row per title surfaced to a user in a search session."""

    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # TMDB metadata
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(10), nullable=False)   # "movie" | "tv"
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    genres: Mapped[str] = mapped_column(Text, default="")                   # pipe-separated
    vote_avg: Mapped[float] = mapped_column(Float, default=0.0)
    popularity: Mapped[float] = mapped_column(Float, default=0.0)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Recommendation context
    score: Mapped[float] = mapped_column(Float, default=0.0)               # score_item result
    rank: Mapped[int] = mapped_column(Integer, default=1)                  # 1, 2, or 3
    search_mode: Mapped[str] = mapped_column(String(20), default="normal") # "normal" | "specific"

    recommended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="history")
