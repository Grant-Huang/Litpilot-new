"""FastAPI application entry point."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tasks import router as tasks_router
from app.api.sessions import router as sessions_router
from app.api.library import router as library_router
from app.api.settings import router as settings_router
from app.tasks.manager import TaskManager

app = FastAPI(
    title="LitPilot API",
    version="0.1.0",
    description="Literature review assistant (simplified)",
)

cors_origins = os.environ.get(
    "LITPILOT_CORS_ORIGINS", "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Task manager (shared across requests)
app.state.task_manager = TaskManager()

# Register API routes
app.include_router(tasks_router)
app.include_router(sessions_router)
app.include_router(library_router)
app.include_router(settings_router)


@app.get("/api/health")
async def health():
    return {"status": "success", "data": {"ok": True}, "message": None}
