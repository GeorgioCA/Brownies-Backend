from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_admin
from core.exceptions import NotFoundException, ValidationException
from models import (
    User, UserPhoto, UserLanguage, VoicePrompt, Match, Swipe, Message,
    BlockReport, Notification, Subscription,
)
from schemas import (
    AdminDashboardOut, AdminReportOut, AdminHandleReportRequest,
    AdminUserOut, AdminUserDetailOut, AdminPhotoOut, AdminVoicePromptOut,
    AdminSubscriptionOut, AdminUserUpdateRequest, SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardOut)
async def get_dashboard(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    active_today = (await db.execute(
        select(func.count()).select_from(User).where(User.last_active >= today_start)
    )).scalar()
    matches_today = (await db.execute(
        select(func.count()).select_from(Match).where(Match.matched_at >= today_start)
    )).scalar()
    reports_pending = (await db.execute(
        select(func.count()).select_from(BlockReport).where(BlockReport.type == "report")
    )).scalar()
    premium_users = (await db.execute(
        select(func.count()).select_from(User).where(User.is_premium == True)
    )).scalar()
    total_photos = (await db.execute(select(func.count()).select_from(UserPhoto))).scalar()
    total_swipes = (await db.execute(select(func.count()).select_from(Swipe))).scalar()
    total_messages = (await db.execute(select(func.count()).select_from(Message))).scalar()

    return AdminDashboardOut(
        total_users=total_users,
        active_users_today=active_today,
        matches_today=matches_today,
        reports_pending=reports_pending,
        premium_users=premium_users,
        total_photos=total_photos,
        total_swipes=total_swipes,
        total_messages=total_messages,
    )


@router.get("/users", response_model=list[AdminUserOut])
async def get_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    search: str = Query(default=""),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    if search:
        stmt = stmt.where(
            (User.name.ilike(f"%{search}%"))
            | (User.phone_number.ilike(f"%{search}%"))
            | (User.city.ilike(f"%{search}%"))
        )
    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    users = result.scalars().all()

    count_stmt = select(func.count()).select_from(User)
    if search:
        count_stmt = count_stmt.where(
            (User.name.ilike(f"%{search}%"))
            | (User.phone_number.ilike(f"%{search}%"))
            | (User.city.ilike(f"%{search}%"))
        )
    total = (await db.execute(count_stmt)).scalar()

    return [
        AdminUserOut(
            id=u.id, name=u.name, phone_number=u.phone_number, city=u.city,
            gender=u.gender, is_active=u.is_active, is_premium=u.is_premium,
            phone_verified=u.phone_verified, photo_verified=u.photo_verified,
            profile_complete=u.profile_complete, created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
async def get_user_detail(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(
            joinedload(User.photos),
            joinedload(User.languages),
            joinedload(User.voice_prompts),
        ).where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    return user


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    req: AdminUserUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    if req.is_active is not None:
        user.is_active = req.is_active
    if req.is_premium is not None:
        user.is_premium = req.is_premium
    if req.photo_verified is not None:
        user.photo_verified = req.photo_verified

    await db.flush()
    return SuccessResponse(message="User updated")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    await db.delete(user)
    await db.flush()
    return SuccessResponse(message="User deleted")


@router.get("/photos", response_model=list[AdminPhotoOut])
async def get_photos(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserPhoto, User.name)
        .join(User, User.id == UserPhoto.user_id)
        .order_by(UserPhoto.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        AdminPhotoOut(
            id=p.id, user_id=p.user_id, user_name=name,
            photo_url=p.photo_url, is_primary=p.is_primary,
            created_at=p.created_at,
        )
        for p, name in rows
    ]


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserPhoto).where(UserPhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise NotFoundException("Photo not found")
    await db.delete(photo)
    await db.flush()
    return SuccessResponse(message="Photo deleted")


@router.get("/voice-prompts", response_model=list[AdminVoicePromptOut])
async def get_voice_prompts(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(VoicePrompt, User.name)
        .join(User, User.id == VoicePrompt.user_id)
        .order_by(VoicePrompt.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        AdminVoicePromptOut(
            id=v.id, user_id=v.user_id, user_name=name,
            prompt_question=v.prompt_question, audio_url=v.audio_url,
            duration_seconds=v.duration_seconds, created_at=v.created_at,
        )
        for v, name in rows
    ]


@router.delete("/voice-prompts/{vp_id}")
async def delete_voice_prompt(
    vp_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VoicePrompt).where(VoicePrompt.id == vp_id))
    vp = result.scalar_one_or_none()
    if not vp:
        raise NotFoundException("Voice prompt not found")
    await db.delete(vp)
    await db.flush()
    return SuccessResponse(message="Voice prompt deleted")


@router.get("/subscriptions", response_model=list[AdminSubscriptionOut])
async def get_subscriptions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Subscription, User.name)
        .join(User, User.id == Subscription.user_id)
        .order_by(Subscription.starts_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        AdminSubscriptionOut(
            id=s.id, user_id=s.user_id, user_name=name,
            plan_type=s.plan_type, starts_at=s.starts_at,
            ends_at=s.ends_at, is_active=s.is_active,
        )
        for s, name in rows
    ]


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
    reports = result.scalars().all()

    user_ids = set()
    for r in reports:
        user_ids.add(r.reporter_id)
        user_ids.add(r.reported_id)
    users_map = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u.name for u in users_result.scalars().all()}

    return [
        AdminReportOut(
            id=r.id, reporter_id=r.reporter_id, reported_id=r.reported_id,
            reporter_name=users_map.get(r.reporter_id, ""), reported_name=users_map.get(r.reported_id, ""),
            reason=r.reason, created_at=r.created_at,
        )
        for r in reports
    ]


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
        raise NotFoundException("Report not found")

    if req.action == "ban":
        user_result = await db.execute(select(User).where(User.id == report.reported_id))
        target = user_result.scalar_one_or_none()
        if target:
            target.is_active = False
    elif req.action == "dismiss":
        pass

    await db.delete(report)
    await db.flush()
    return SuccessResponse(message=f"Report handled: {req.action}")


@router.get("/stats/gender")
async def get_gender_stats(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User.gender, func.count()).group_by(User.gender)
    )
    return {g: c for g, c in result.all()}


@router.get("/stats/cities")
async def get_city_stats(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User.city, func.count()).group_by(User.city).order_by(func.count().desc()).limit(20)
    )
    return [{"city": c, "count": cnt} for c, cnt in result.all() if c]
