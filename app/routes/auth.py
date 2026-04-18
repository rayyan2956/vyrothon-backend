"""POST /auth/selfie — Authenticate a person via selfie face matching."""

import os
import tempfile

from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import AuthResponse
from app.face_service import extract_embeddings, find_matching_grab_id

router = APIRouter()


@router.post("/selfie", response_model=AuthResponse)
async def authenticate_selfie(
    selfie: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user by matching their selfie against known face embeddings.
    """
    temp_path = None
    try:
        # Save selfie to a temporary file
        suffix = os.path.splitext(selfie.filename or "selfie.jpg")[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await selfie.read()
            tmp.write(content)
            temp_path = tmp.name

        # Extract embeddings from the selfie
        embeddings = extract_embeddings(temp_path)

        if not embeddings:
            raise HTTPException(
                status_code=400,
                detail="No face detected in the provided image",
            )

        # If multiple faces detected, use the largest one (by area w*h)
        if len(embeddings) > 1:
            best_face = max(
                embeddings,
                key=lambda f: f["facial_area"].get("w", 0) * f["facial_area"].get("h", 0),
            )
        else:
            best_face = embeddings[0]

        # Search for a matching GrabID
        grab_id = await find_matching_grab_id(db, best_face["embedding"])

        if grab_id is None:
            raise HTTPException(
                status_code=401,
                detail="Face not recognized. Not in the system.",
            )

        return AuthResponse(
            authenticated=True,
            grab_id=grab_id,
            message="Identity verified successfully",
        )

    finally:
        # Always clean up the temp file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
