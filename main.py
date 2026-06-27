from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .core.config import settings
from .core.database import init_db
from .routers import auth, profile, discovery, matches, notifications, reports, family, verification, preferences, subscriptions, admin
from .websocket.handler import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
