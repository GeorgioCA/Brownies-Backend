from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import shutil
import uuid

from ..core.config import settings
from ..core.database import get_db
from ..core.auth_deps import get_current_user, get_premium_user
from ..core.exceptions import ValidationException, NotFoundException
from ..models import User, UserPhoto, UserLanguage, VoicePrompt
from ..schemas import (
    SetupProfileRequest, UpdateProfileRequest, UpdateLanguagesRequest,
    ReorderPhotosRequest, VoicePromptCreate,
    UserProfileOut, UserPhotoOut, UserLanguageOut, VoicePromptOut,
    SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/profile", tags=["profile"])


def calculate_age(dob_str: str) -> int:
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        return 0


def profile_to_out(user: User) -> UserProfileOut:
    age = calculate_age(user.date_of_birth) if user.date_of_birth else 0
    return UserProfileOut(
        id=user.id,
        name=user.name,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        bio=user.bio,
        intent=user.intent,
        city=user.city,
        college=user.college,
        workplace=user.workplace,
        height_cm=user.height_cm,
        religion=user.religion,
        education=user.education,
        occupation=user.occupation,
        phone_verified=user.phone_verified,
        photo_verified=user.photo_verified,
        profile_complete=user.profile_complete,
        is_premium=user.is_premium,
        preferred_language=user.preferred_language,
        show_online_status=user.show_online_status,
        last_active=user.last_active,
        photos=[UserPhotoOut.model_validate(p) for p in (user.photos or [])],
        languages=[UserLanguageOut.model_validate(l) for l in (user.languages or [])],
        voice_prompts=[VoicePromptOut.model_validate(v) for v in (user.voice_prompts or [])],
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserProfileOut)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user.id)
    )
    user = result.scalar_one()
    return profile_to_out(user)


@router.post("/setup", response_model=UserProfileOut)
async def setup_profile(
    req: SetupProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.name = req.name
    user.date_of_birth = req.date_of_birth
    user.gender = req.gender
    user.intent = req.intent
    user.city = req.city
    user.bio = req.bio
    user.college = req.college
    user.workplace = req.workplace
    user.height_cm = req.height_cm
    user.religion = req.religion
    user.education = req.education
    user.occupation = req.occupation
    user.preferred_language = req.preferred_language
    user.profile_complete = True
    user.updated_at = datetime.now(timezone.utc)

    # Clear existing languages and set new
    result = await db.execute(select(UserLanguage).where(UserLanguage.user_id == user.id))
    for lang in result.scalars().all():
        await db.delete(lang)
    for lang in req.languages:
        db.add(UserLanguage(user_id=user.id, language=lang))

    await db.flush()
    result = await db.execute(select(User).where(User.id == user.id))
    return profile_to_out(result.scalar_one())


@router.patch("/me", response_model=UserProfileOut)
async def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()
    result = await db.execute(select(User).where(User.id == user.id))
    return profile_to_out(result.scalar_one())


@router.post("/photos", response_model=UserPhotoOut)
async def upload_photo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPhoto).where(UserPhoto.user_id == user.id)
    )
    existing = result.scalars().all()
    if len(existing) >= settings.MAX_PHOTOS_PER_USER:
        raise ValidationException(f"Maximum {settings.MAX_PHOTOS_PER_USER} photos allowed")

    ext = Path(file.filename or "photo.jpg").suffix or ".jpg"
    filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
    filepath = settings.UPLOAD_DIR / "photos" / filename
    with filepath.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    is_primary = len(existing) == 0
    photo = UserPhoto(
        user_id=user.id,
        photo_url=f"/api/v1/uploads/photos/{filename}",
        is_primary=is_primary,
        sort_order=len(existing),
    )
    db.add(photo)
    await db.flush()
    if not user.photo_verified and len(existing) >= 1:
        user.photo_verified = False  # Requires admin/manual verification
    return UserPhotoOut.model_validate(photo)


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPhoto).where(UserPhoto.id == photo_id, UserPhoto.user_id == user.id)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise NotFoundException("Photo not found")

    filepath = settings.UPLOAD_DIR / "photos" / Path(photo.photo_url).name
    if filepath.exists():
        filepath.unlink()

    await db.delete(photo)
    return SuccessResponse(message="Photo deleted")


@router.put("/photos/reorder")
async def reorder_photos(
    req: ReorderPhotosRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPhoto).where(UserPhoto.user_id == user.id)
    )
    photos = {p.id: p for p in result.scalars().all()}
    for idx, pid in enumerate(req.photo_ids):
        if pid in photos:
            photos[pid].sort_order = idx
    return SuccessResponse(message="Photos reordered")


@router.get("/voice-prompts", response_model=list[VoicePromptOut])
async def get_voice_prompts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VoicePrompt).where(VoicePrompt.user_id == user.id)
    )
    return [VoicePromptOut.model_validate(v) for v in result.scalars().all()]


@router.post("/voice-prompts", response_model=VoicePromptOut)
async def create_voice_prompt(
    audio: UploadFile = File(...),
    prompt_question: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = Path(audio.filename or "audio.m4a").suffix or ".m4a"
    filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
    filepath = settings.UPLOAD_DIR / "voice" / filename
    with filepath.open("wb") as f:
        shutil.copyfileobj(audio.file, f)

    vp = VoicePrompt(
        user_id=user.id,
        prompt_question=prompt_question,
        audio_url=f"/api/v1/uploads/voice/{filename}",
    )
    db.add(vp)
    await db.flush()
    return VoicePromptOut.model_validate(vp)


@router.delete("/voice-prompts/{vp_id}")
async def delete_voice_prompt(
    vp_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VoicePrompt).where(VoicePrompt.id == vp_id, VoicePrompt.user_id == user.id)
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise NotFoundException("Voice prompt not found")

    filepath = settings.UPLOAD_DIR / "voice" / Path(vp.audio_url).name
    if filepath.exists():
        filepath.unlink()

    await db.delete(vp)
    return SuccessResponse(message="Voice prompt deleted")


@router.put("/languages")
async def update_languages(
    req: UpdateLanguagesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserLanguage).where(UserLanguage.user_id == user.id))
    for lang in result.scalars().all():
        await db.delete(lang)
    for lang in req.languages:
        db.add(UserLanguage(user_id=user.id, language=lang))
    return SuccessResponse(message=f"Languages updated: {req.languages}")


@router.get("/{user_id}", response_model=UserProfileOut)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundException("User not found")
    return profile_to_out(target)
