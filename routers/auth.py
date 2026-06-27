from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import (
    generate_otp, store_otp, verify_otp, check_otp_rate_limit,
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token,
)
from core.exceptions import AuthException, ConflictException, RateLimitException
from core.auth_deps import get_current_user
from models import User
from schemas import (
    SendOtpRequest, VerifyOtpRequest, SetPasswordRequest, LoginRequest,
    RefreshTokenRequest, TokenResponse, SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])


@router.post("/send-otp")
async def send_otp(req: SendOtpRequest):
    phone = req.phone_number.strip()
    allowed, retry_after = check_otp_rate_limit(phone)
    if not allowed:
        raise RateLimitException(
            f"Too many OTP requests. Try again in {retry_after}s",
            retry_after=retry_after,
        )
    otp = generate_otp()
    store_otp(phone, otp)
    # In production: send via Twilio. For dev, log it.
    return {
        "success": True,
        "retry_after_seconds": 30,
        "expires_in_seconds": settings.OTP_EXPIRE_SECONDS,
        "otp": otp,  # ONLY for development
    }


@router.post("/verify-otp")
async def verify_otp_endpoint(req: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    phone = req.phone_number.strip()
    if not verify_otp(phone, req.otp):
        from core.exceptions import ValidationException
        raise ValidationException("Invalid or expired OTP")

    result = await db.execute(select(User).where(User.phone_number == phone))
    user = result.scalar_one_or_none()

    if user:
        user.phone_verified = True
        access = create_access_token({"sub": str(user.id)})
        refresh = create_refresh_token({"sub": str(user.id)})
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "is_new_user": False,
            "profile_complete": user.profile_complete,
        }

    password_hash = hash_password(phone)  # temporary password
    new_user = User(
        phone_number=phone,
        phone_verified=True,
        password_hash=password_hash,
        name="",
        date_of_birth="",
        gender="",
        city="",
    )
    db.add(new_user)
    await db.flush()
    access = create_access_token({"sub": str(new_user.id)})
    refresh = create_refresh_token({"sub": str(new_user.id)})
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "is_new_user": True,
        "profile_complete": False,
    }


@router.post("/set-password")
async def set_password(
    req: SetPasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.password_hash = hash_password(req.password)
    return {"success": True, "message": "Password set"}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone_number == req.phone_number.strip()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise AuthException("Invalid phone or password")
    if not user.is_active:
        raise AuthException("Account is deactivated")
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh")
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthException("Invalid or expired refresh token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthException("User not found or inactive")
    access = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout")
async def logout():
    return SuccessResponse(message="Logged out")


@router.delete("/account")
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.delete(user)
    return SuccessResponse(message="Account deleted")
