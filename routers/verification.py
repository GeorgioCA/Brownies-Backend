from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import shutil
import uuid

from ..core.config import settings
from ..core.database import get_db
from ..core.auth_deps import get_current_user
from ..schemas import VerificationStatusOut, SuccessResponse

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/verification", tags=["verification"])


@router.get("/status", response_model=VerificationStatusOut)
async def verification_status(user=Depends(get_current_user)):
    return VerificationStatusOut(
        phone_verified=user.phone_verified,
        photo_verified=user.photo_verified,
    )


@router.post("/phone/send-otp")
async def send_phone_verification_otp(user=Depends(get_current_user)):
    from ..core.security import generate_otp, store_otp
    otp = generate_otp()
    store_otp(user.phone_number, otp)
    return {"success": True, "expires_in_seconds": settings.OTP_EXPIRE_SECONDS, "otp": otp}


@router.post("/phone/verify")
async def verify_phone(otp: str, user=Depends(get_current_user)):
    from ..core.security import verify_otp
    if verify_otp(user.phone_number, otp):
        user.phone_verified = True
        return SuccessResponse(message="Phone verified")
    from ..core.exceptions import ValidationException
    raise ValidationException("Invalid OTP")


@router.post("/photo")
async def submit_photo_verification(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    filename = f"verify_{user.id}_{uuid.uuid4().hex}.jpg"
    filepath = settings.UPLOAD_DIR / "verification" / filename
    with filepath.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # In production: run facial recognition matching
    # For dev: auto-verify
    user.photo_verified = True
    return SuccessResponse(message="Photo verification submitted")
