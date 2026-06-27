from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_user, get_premium_user
from core.geo import haversine_distance
from core.exceptions import ValidationException, NotFoundException, PaymentRequiredException
from models import User, UserPhoto, UserLanguage, VoicePrompt, Swipe, Match, BlockReport, Notification
from schemas import (
    DiscoveryProfileOut, UserPhotoOut, UserLanguageOut, VoicePromptOut,
    SwipeRequest, SwipeStatsOut, SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}", tags=["discovery"])


def _discovery_out(user: User, current_user: User) -> DiscoveryProfileOut:
    dob = user.date_of_birth
    age = 0
    if dob:
        try:
            d = datetime.strptime(dob, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except (ValueError, TypeError):
            pass

    dist = None
    if current_user.location_lat is not None and user.location_lat is not None:
        dist = round(haversine_distance(
            current_user.location_lat, current_user.location_lng,
            user.location_lat, user.location_lng,
        ), 1)

    return DiscoveryProfileOut(
        id=user.id,
        name=user.name,
        age=age,
        gender=user.gender,
        city=user.city,
        intent=user.intent,
        bio=user.bio,
        height_cm=user.height_cm,
        religion=user.religion,
        education=user.education,
        occupation=user.occupation,
        college=user.college,
        workplace=user.workplace,
        photo_verified=user.photo_verified,
        distance_km=dist,
        photos=[UserPhotoOut.model_validate(p) for p in (user.photos or [])],
        languages=[UserLanguageOut.model_validate(l) for l in (user.languages or [])],
        voice_prompts=[VoicePromptOut.model_validate(v) for v in (user.voice_prompts or [])],
    )


@router.get("/discovery", response_model=list[DiscoveryProfileOut])
async def get_discovery(
    per_page: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get already swiped / blocked user IDs
    swiped_sub = select(Swipe.swiped_id).where(Swipe.swiper_id == user.id)
    blocked_sub = select(BlockReport.reported_id).where(
        BlockReport.reporter_id == user.id, BlockReport.type == "block"
    )
    blocked_me_sub = select(BlockReport.reporter_id).where(
        BlockReport.reported_id == user.id, BlockReport.type == "block"
    )
    all_exclude = swiped_sub.union(blocked_sub).union(blocked_me_sub)
    exclude_result = await db.execute(all_exclude)
    exclude_ids = {row[0] for row in exclude_result}

    # Build query for discoverable users
    stmt = (
        select(User)
        .where(
            User.id != user.id,
            User.profile_complete == True,
            User.is_active == True,
            User.id.not_in(exclude_ids) if exclude_ids else True,
            User.gender != user.gender,  # Opposite gender for now; customizable via prefs later
        )
        .limit(per_page)
    )

    # Apply user preferences filters
    # (Pulled from user_preferences attached to this user; loaded via relationship)
    # For simplicity, we apply basic filters inline
    if user.intent:
        stmt = stmt.where(User.intent == user.intent)

    # City filtering — prefer same city
    if user.city:
        stmt = stmt.order_by(
            func.case((User.city == user.city, 0), else_=1)
        )

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    profiles = [_discovery_out(u, user) for u in candidates]

    # Sort by distance if location available
    if user.location_lat is not None:
        profiles.sort(key=lambda p: p.distance_km or 99999)

    return profiles


@router.post("/swipes")
async def create_swipe(
    req: SwipeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.swiped_id == user.id:
        raise ValidationException("Cannot swipe on yourself")

    # Check target exists
    target_result = await db.execute(select(User).where(User.id == req.swiped_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise NotFoundException("User not found")

    # Check already swiped
    exist_result = await db.execute(
        select(Swipe).where(Swipe.swiper_id == user.id, Swipe.swiped_id == req.swiped_id)
    )
    if exist_result.scalar_one_or_none():
        raise ValidationException("Already swiped on this user")

    # Daily limits check
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_swipes = await db.execute(
        select(func.count()).select_from(Swipe).where(
            Swipe.swiper_id == user.id,
            Swipe.created_at >= today_start,
        )
    )
    count = today_swipes.scalar()

    if req.direction == "super_like":
        today_super = await db.execute(
            select(func.count()).select_from(Swipe).where(
                Swipe.swiper_id == user.id,
                Swipe.direction == "super_like",
                Swipe.created_at >= today_start,
            )
        )
        super_count = today_super.scalar()
        max_super = settings.DAILY_SUPER_LIKES_FREE
        if user.is_premium:
            max_super = 999
        if super_count >= max_super:
            raise PaymentRequiredException("Daily super like limit reached")
    else:
        max_likes = settings.DAILY_LIKES_FREE
        if user.is_premium:
            max_likes = 999
        if count >= max_likes:
            raise PaymentRequiredException("Daily like limit reached")

    swipe = Swipe(
        swiper_id=user.id,
        swiped_id=req.swiped_id,
        direction=req.direction,
    )
    db.add(swipe)

    response_data = {"success": True, "direction": req.direction}

    # Check for match: if target also swiped right on me
    if req.direction in ("like", "super_like"):
        mutual = await db.execute(
            select(Swipe).where(
                Swipe.swiper_id == req.swiped_id,
                Swipe.swiped_id == user.id,
                Swipe.direction.in_(("like", "super_like")),
            )
        )
        if mutual.scalar_one_or_none():
            # Create match
            u1, u2 = (user.id, req.swiped_id) if user.id < req.swiped_id else (req.swiped_id, user.id)
            match = Match(user1_id=u1, user2_id=u2)
            db.add(match)

            # Notify both users
            db.add(Notification(
                user_id=user.id, type="match",
                title="New Match!", body=f"You matched with {target.name}",
                related_user_id=req.swiped_id,
            ))
            db.add(Notification(
                user_id=req.swiped_id, type="match",
                title="New Match!", body=f"You matched with {user.name}",
                related_user_id=user.id,
            ))

            await db.flush()
            response_data["match_id"] = match.id
            response_data["matched"] = True
            return response_data

    await db.flush()
    response_data["matched"] = False
    return response_data


@router.post("/swipes/undo")
async def undo_swipe(
    user: User = Depends(get_premium_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Swipe).where(Swipe.swiper_id == user.id).order_by(Swipe.created_at.desc()).limit(1)
    )
    last_swipe = result.scalar_one_or_none()
    if not last_swipe:
        raise NotFoundException("No swipe to undo")
    await db.delete(last_swipe)
    return SuccessResponse(message="Swipe undone")


@router.get("/swipes/stats", response_model=SwipeStatsOut)
async def get_swipe_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    likes = await db.execute(
        select(func.count()).select_from(Swipe).where(
            Swipe.swiper_id == user.id,
            Swipe.created_at >= today_start,
        )
    )
    super_likes = await db.execute(
        select(func.count()).select_from(Swipe).where(
            Swipe.swiper_id == user.id,
            Swipe.direction == "super_like",
            Swipe.created_at >= today_start,
        )
    )
    max_likes = settings.DAILY_LIKES_FREE if not user.is_premium else 999
    max_super = settings.DAILY_SUPER_LIKES_FREE if not user.is_premium else 999
    return SwipeStatsOut(
        likes_remaining=max(0, max_likes - likes.scalar()),
        super_likes_remaining=max(0, max_super - super_likes.scalar()),
    )
