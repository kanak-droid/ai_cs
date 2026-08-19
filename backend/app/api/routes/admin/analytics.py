from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.schemas.analytics import AnalyticsOverview
from app.services import analytics_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/analytics", response_model=AnalyticsOverview)
def get_analytics_overview(
    priority: Literal["1", "2", "3", "4", "5", "unranked"] | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AnalyticsOverview:
    return AnalyticsOverview(
        **analytics_service.get_overview(db, priority=priority, date_from=date_from, date_to=date_to)
    )
