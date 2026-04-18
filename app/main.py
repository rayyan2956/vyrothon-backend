"""
Grabpic API — FastAPI application entry point.

Lifespan manages DB initialization and uploads directory creation.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.schemas import HealthResponse
from app.routes import ingest, auth, images


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup: initialize DB and create uploads directory
    print("[grabpic] Initializing database...")
    await init_db()
    print("[grabpic] Database initialized successfully.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"[grabpic] Upload directory ensured: {settings.UPLOAD_DIR}")

    yield

    # Shutdown (nothing to clean up for now)
    print("[grabpic] Shutting down.")


app = FastAPI(
    title="Grabpic API",
    version="1.0.0",
    description=(
        "High-performance facial recognition backend for large-scale events. "
        "Ingest event photos, detect and cluster faces, and let attendees "
        "authenticate via selfie to retrieve their photos."
    ),
    lifespan=lifespan,
)

# CORS — allow all origins (hackathon mode)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(images.router, tags=["Images"])


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    return HealthResponse(status="ok", service="grabpic")
