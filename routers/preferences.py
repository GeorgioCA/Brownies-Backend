from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.auth_deps import get_current_user
from ..core.exceptions import NotFoundException
from ..models import UserPreferences
from ..schemas import (
    PreferencesOut, UpdatePreferencesRequest,
    UpdateNotificationSettingsRequest,
    SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesOut)
async def get_preferences(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        await db.flush()
    return PreferencesOut.model_validate(prefs)


@router.put("", response_model=PreferencesOut)
async def update_preferences(
    req: UpdatePreferencesRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)

    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(prefs, key, value)

    await db.flush()
    return PreferencesOut.model_validate(prefs)


@router.put("/notification-settings")
async def update_notification_settings(
    req: UpdateNotificationSettingsRequest,
    user=Depends(get_current_user),
):
    if req.show_online_status is not None:
        user.show_online_status = req.show_online_status
    if req.show_distance is not None:
        user.show_distance = req.show_distance
    return SuccessResponse(message="Settings updated")
