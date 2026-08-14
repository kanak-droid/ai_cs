from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.services import sheets_sync_service

router = APIRouter(tags=["admin"])


@router.post("/api/admin/sync-sheets")
def sync_sheets(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    """Manual trigger for the same sync the daily cron runs — lets ops pull
    fresh data right after editing a sheet instead of waiting for the next
    scheduled run.
    """
    return sheets_sync_service.sync_all(db)
