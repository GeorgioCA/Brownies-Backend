from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.auth_deps import get_current_user
from ..schemas import NotificationOut, SuccessResponse

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["notifications"])

from ..models import Notification


@router.get("", response_model=list[NotificationOut])
async def get_notifications(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]


@router.get("/unread-count")
async def get_unread_count(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    return {"unread_count": result.scalar()}


@router.put("/{notif_id}/read")
async def mark_read(
    notif_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == notif_id, Notification.user_id == user.id)
    )
    notif = result.scalar_one_or_none()
    if notif:
        notif.is_read = True
    return SuccessResponse(message="Marked as read")


@router.put("/read-all")
async def mark_all_read(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.is_read == False)
    )
    for n in result.scalars().all():
        n.is_read = True
    return SuccessResponse(message="All marked as read")


@router.post("/push-token")
async def register_push_token(
    token: str,
    user=Depends(get_current_user),
):
    # In production: store FCM token
    return SuccessResponse(message="Push token registered")
