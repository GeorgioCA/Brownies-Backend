from datetime import datetime, timezone, timedelta
import secrets
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.auth_deps import get_current_user
from ..core.exceptions import NotFoundException, ForbiddenException
from ..models import User, UserPhoto, VoicePrompt, FamilyShare, Match
from ..schemas import (
    FamilyShareRequest, FamilyShareOut,
    SharedProfileOut, UserPhotoOut, VoicePromptOut,
    SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}", tags=["family-share"])


@router.post("/family-share/{match_id}", response_model=FamilyShareOut)
async def create_family_share(
    match_id: int,
    req: FamilyShareRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match or user.id not in (match.user1_id, match.user2_id):
        raise ForbiddenException("Not your match")

    profile_id = match.user2_id if match.user1_id == user.id else match.user1_id

    token = secrets.token_urlsafe(settings.FAMILY_SHARE_TOKEN_LENGTH)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.FAMILY_SHARE_EXPIRE_DAYS)

    share = FamilyShare(
        user_id=user.id,
        profile_user_id=profile_id,
        shared_with_email=req.shared_with_email,
        shared_with_phone=req.shared_with_phone,
        access_token=token,
        expires_at=expires,
    )
    db.add(share)
    await db.flush()

    return FamilyShareOut(
        id=share.id,
        profile_user_id=profile_id,
        share_url=f"{settings.API_V1_PREFIX}/shared/{token}",
        expires_at=expires,
    )


@router.get("/shared/{token}", response_model=SharedProfileOut)
async def view_shared_profile(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamilyShare).where(FamilyShare.access_token == token)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise NotFoundException("Share link not found")
    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        raise ForbiddenException("Share link has expired")

    profile_result = await db.execute(
        select(User).where(User.id == share.profile_user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise NotFoundException("Profile not found")

    dob = profile.date_of_birth
    age = 0
    if dob:
        try:
            d = datetime.strptime(dob, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except (ValueError, TypeError):
            pass

    return SharedProfileOut(
        name=profile.name,
        age=age,
        city=profile.city,
        intent=profile.intent,
        bio=profile.bio,
        education=profile.education,
        occupation=profile.occupation,
        photos=[UserPhotoOut.model_validate(p) for p in (profile.photos or [])],
        voice_prompts=[VoicePromptOut.model_validate(v) for v in (profile.voice_prompts or [])],
    )


@router.delete("/family-share/{share_id}")
async def revoke_share(
    share_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamilyShare).where(FamilyShare.id == share_id, FamilyShare.user_id == user.id)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise NotFoundException("Share not found")
    await db.delete(share)
    return SuccessResponse(message="Share revoked")
