from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ---------- Ingest ----------

class IngestResult(BaseModel):
    """Result for a single ingested image."""
    image_id: UUID
    filename: str
    faces_found: int
    grab_ids: list[UUID]


class IngestResponse(BaseModel):
    """Response for the POST /ingest endpoint."""
    ingested: list[IngestResult]
    total_images: int
    total_faces_found: int


# ---------- Auth ----------

class AuthResponse(BaseModel):
    """Response for the POST /auth/selfie endpoint."""
    authenticated: bool
    grab_id: UUID
    message: str


# ---------- Images ----------

class ImageDetail(BaseModel):
    """Detail for a single image linked to a GrabID."""
    image_id: UUID
    filename: str
    file_path: str
    face_area: Optional[dict] = None
    ingested_at: datetime


class ImagesResponse(BaseModel):
    """Response for the GET /images/{grab_id} endpoint."""
    grab_id: UUID
    total_images: int
    images: list[ImageDetail]


# ---------- Health ----------

class HealthResponse(BaseModel):
    """Response for the GET /health endpoint."""
    status: str
    service: str
