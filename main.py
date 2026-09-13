"""FastAPI application and routes."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.ideas import router as ideas_router
from core.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Money Factory - Multi-Agent Idea Factory",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ideas_router, prefix="/ideas", tags=["ideas"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.APP_NAME}

    return app


app = create_app()
