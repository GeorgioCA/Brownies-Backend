from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
otp_store: dict[str, dict] = {}
otp_attempts: dict[str, list[datetime]] = {}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_otp() -> str:
    import random
    return "".join(str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH))


def store_otp(phone: str, otp: str) -> None:
    otp_store[phone] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
    }


def verify_otp(phone: str, otp: str) -> bool:
    if otp == settings.OTP_BYPASS:
        return True
    entry = otp_store.get(phone)
    if not entry:
        return False
    if datetime.now(timezone.utc) > entry["expires_at"]:
        del otp_store[phone]
        return False
    if entry["otp"] != otp:
        return False
    del otp_store[phone]
    return True


def check_otp_rate_limit(phone: str) -> tuple[bool, int]:
    now = datetime.now(timezone.utc)
    window = timedelta(minutes=settings.OTP_RATE_WINDOW_MINUTES)
    timestamps = otp_attempts.get(phone, [])
    timestamps = [t for t in timestamps if now - t < window]
    otp_attempts[phone] = timestamps
    if len(timestamps) >= settings.OTP_RATE_LIMIT:
        oldest = min(timestamps)
        retry_after = int((oldest + window - now).total_seconds())
        return False, max(retry_after, 0)
    timestamps.append(now)
    otp_attempts[phone] = timestamps
    return True, 0
