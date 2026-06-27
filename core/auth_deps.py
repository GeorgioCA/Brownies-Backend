from datetime import datetime, timezone

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token
from core.exceptions import AuthException, ForbiddenException
from models import User


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise AuthException("Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise AuthException("Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise AuthException("Invalid token payload")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthException("User not found or inactive")
    user.last_active = datetime.now(timezone.utc)
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    # For now, no admin role column — premium users or a hardcoded list
    # In production, add a role column
    return user


async def get_premium_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_premium:
        from core.exceptions import PaymentRequiredException
        raise PaymentRequiredException()
    return user
