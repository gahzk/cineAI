# -*- coding: utf-8 -*-
"""UserPreference ORM model — stores the user's last search profile."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserPreference(Base):
    """Persists a user's preference profile (replaces the terminal ask_ panels)."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Content type: "movie" | "tv" | "" (both)
    content_type: Mapped[str] = mapped_column(String(10), default="")

    # Pipe-separated genre lists  e.g. "Ação|Crime"
    genres_include: Mapped[str] = mapped_column(Text, default="")
    genres_exclude: Mapped[str] = mapped_column(Text, default="")

    # Duration preference: "Curta" | "Média" | "Longa" | "Qualquer"
    duration_pref: Mapped[str] = mapped_column(String(20), default="Qualquer")

    # Score weights
    weight_rating: Mapped[float] = mapped_column(Float, default=0.8)
    weight_popularity: Mapped[float] = mapped_column(Float, default=0.8)

    # Flags
    prefer_new: Mapped[bool] = mapped_column(default=False)
    classic_focus: Mapped[bool] = mapped_column(default=False)

    # Specific search extras (nullable — only set when using specific mode)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    director: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    network: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_vote: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="preferences")
