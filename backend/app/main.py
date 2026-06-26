from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .database import init_db
from .routers import analytics, model, motion, sessions, users


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(motion.router, prefix="/api/motion", tags=["motion"])
app.include_router(model.router, prefix="/api/model", tags=["model"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
