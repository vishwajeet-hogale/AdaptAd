"""
AdaptAd FastAPI application entry point.

Start with: uvicorn backend.main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .db.database import init_db
from .api.routes_data import router as data_router
from .api.routes_evolve import router as evolve_router
from .api.routes_decide import router as decide_router
from .api.routes_simulate import router as simulate_router
from .api.routes_ab import router as ab_router
from .api.routes_experiments import router as experiments_router
from .api.websocket import router as ws_router

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="AdaptAd",
    description="Human-centered ad decision system for streaming platforms.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_router)
app.include_router(evolve_router)
app.include_router(decide_router)
app.include_router(simulate_router)
app.include_router(ab_router)
app.include_router(experiments_router)
app.include_router(ws_router)

# Serve React frontend if built (production / Render deployment).
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Catch-all: return index.html so React Router handles client-side routes."""
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")

else:
    @app.get("/")
    def root():
        return {
            "project": "AdaptAd",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/health",
        }
