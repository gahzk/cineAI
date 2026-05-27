# -*- coding: utf-8 -*-
"""Analytics router — admin dashboard data endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_admin_user
from app.schemas.analytics import AnalyticsSummary
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated analytics for the admin dashboard."""
    data = await analytics.get_summary(db)
    return AnalyticsSummary(**data)
