from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
frontend_assets_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "assets"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.manifests_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount(
    "/assets", StaticFiles(directory=frontend_assets_dir, check_dir=False), name="frontend-assets"
)
app.include_router(api_router)
