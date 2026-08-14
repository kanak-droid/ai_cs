from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.schemas.analytics import AnalyticsOverview
from app.services import analytics_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/analytics", response_model=AnalyticsOverview)
def get_analytics_overview(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AnalyticsOverview:
    return AnalyticsOverview(**analytics_service.get_overview(db))
