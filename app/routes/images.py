"""GET /images/{grab_id} — Retrieve all images linked to a GrabID."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import GrabID, Image, ImageGrabID
from app.schemas import ImageDetail, ImagesResponse

router = APIRouter()


@router.get("/images/{grab_id}", response_model=ImagesResponse)
async def get_images_by_grab_id(
    grab_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all images associated with a given GrabID.
    """
    # Check if grab_id exists
    result = await db.execute(
        select(GrabID).where(GrabID.id == grab_id)
    )
    grab = result.scalar_one_or_none()

    if grab is None:
        raise HTTPException(status_code=404, detail="grab_id not found")

    # Fetch all images linked to this grab_id
    query = (
        select(Image, ImageGrabID.face_area)
        .join(ImageGrabID, Image.id == ImageGrabID.image_id)
        .where(ImageGrabID.grab_id == grab_id)
        .order_by(Image.ingested_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    images = [
        ImageDetail(
            image_id=image.id,
            filename=image.original_filename,
            file_path=image.file_path,
            face_area=face_area,
            ingested_at=image.ingested_at,
        )
        for image, face_area in rows
    ]

    return ImagesResponse(
        grab_id=grab_id,
        total_images=len(images),
        images=images,
    )
