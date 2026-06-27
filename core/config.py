from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Brownies Dating App"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://brownies:brownies@localhost:5432/brownies"
    DATABASE_ECHO: bool = False

    JWT_SECRET: str = "brownies-dev-secret-replace-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    OTP_BYPASS: str = "123456"
    OTP_LENGTH: int = 6
    OTP_EXPIRE_SECONDS: int = 300
    OTP_RATE_LIMIT: int = 3
    OTP_RATE_WINDOW_MINUTES: int = 10

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE: str = ""

    UPLOAD_DIR: Path = Path("data/uploads")
    MAX_PHOTO_SIZE_MB: int = 10
    MAX_PHOTOS_PER_USER: int = 6
    MAX_VOICE_DURATION_SECONDS: int = 60

    DAILY_LIKES_FREE: int = 50
    DAILY_SUPER_LIKES_FREE: int = 1

    FAMILY_SHARE_EXPIRE_DAYS: int = 7
    FAMILY_SHARE_TOKEN_LENGTH: int = 32

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
