from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from core.config import settings
from core.database import init_db, engine
from routers import auth, profile, discovery, matches, notifications, reports, family, verification, preferences, subscriptions, admin
from websocket.handler import router as ws_router


async def load_runtime_settings():
    from sqlalchemy import select, text
    async with engine.connect() as conn:
        try:
            result = await conn.execute(text("SELECT key, value FROM app_settings"))
            for key, val in result:
                if key == "daily_likes_free":
                    settings.DAILY_LIKES_FREE = int(val)
                elif key == "daily_super_likes_free":
                    settings.DAILY_SUPER_LIKES_FREE = int(val)
                elif key == "max_photos_per_user":
                    settings.MAX_PHOTOS_PER_USER = int(val)
                elif key == "max_photo_size_mb":
                    settings.MAX_PHOTO_SIZE_MB = int(val)
                elif key == "max_voice_duration_seconds":
                    settings.MAX_VOICE_DURATION_SECONDS = int(val)
                elif key == "family_share_expire_days":
                    settings.FAMILY_SHARE_EXPIRE_DAYS = int(val)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await load_runtime_settings()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(discovery.router)
app.include_router(matches.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(family.router)
app.include_router(verification.router)
app.include_router(preferences.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)
app.include_router(ws_router)

# Static file serving for uploads
import os
upload_dir = settings.UPLOAD_DIR
upload_dir.mkdir(parents=True, exist_ok=True)
(upload_dir / "photos").mkdir(parents=True, exist_ok=True)
(upload_dir / "voice").mkdir(parents=True, exist_ok=True)
(upload_dir / "verification").mkdir(parents=True, exist_ok=True)
app.mount("/api/v1/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Admin dashboard static files
static_dir = Path("static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/admin", StaticFiles(directory="static/admin", html=True), name="admin")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
