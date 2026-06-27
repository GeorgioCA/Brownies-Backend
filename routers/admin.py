from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.auth_deps import get_current_admin
from ..models import User, Match, BlockReport
from ..schemas import (
    AdminDashboardOut, AdminReportOut, AdminHandleReportRequest,
    AdminUserOut, SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardOut)
async def get_dashboard(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(select(func.count()).select_from(User))
    total_users = total_result.scalar()

    today = datetime.now(timezone.utc).date()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    active_result = await db.execute(
        select(func.count()).select_from(User).where(User.last_active >= today_start)
    )
    active_today = active_result.scalar()

    matches_result = await db.execute(
        select(func.count()).select_from(Match).where(Match.matched_at >= today_start)
    )
    matches_today = matches_result.scalar()

    reports_result = await db.execute(
        select(func.count()).select_from(BlockReport).where(BlockReport.type == "report")
    )
    reports_pending = reports_result.scalar()

    return AdminDashboardOut(
        total_users=total_users,
        active_users_today=active_today,
        matches_today=matches_today,
        reports_pending=reports_pending,
    )


@router.get("/reports", response_model=list[AdminReportOut])
async def get_reports(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BlockReport)
        .where(BlockReport.type == "report")
        .order_by(BlockReport.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return [AdminReportOut.model_validate(r) for r in result.scalars().all()]


@router.post("/reports/{report_id}/action")
async def handle_report(
    report_id: int,
    req: AdminHandleReportRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BlockReport).where(BlockReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        from ..core.exceptions import NotFoundException
        from ..core.exceptions import NotFoundException as NotFoundException2
        raise NotFoundException("Report not found")

    if req.action == "ban":
        user_result = await db.execute(select(User).where(User.id == report.reported_id))
        target = user_result.scalar_one_or_none()
        if target:
            target.is_active = False

    return SuccessResponse(message=f"Report handled: {req.action}")


@router.get("/users", response_model=list[AdminUserOut])
async def get_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return [AdminUserOut.model_validate(u) for u in result.scalars().all()]
