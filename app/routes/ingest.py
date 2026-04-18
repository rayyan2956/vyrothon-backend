"""POST /ingest — Bulk image ingestion with face detection and clustering."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.models import Image, ImageGrabID
from app.schemas import IngestResult, IngestResponse
from app.face_service import extract_embeddings, get_or_create_grab_id

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_images(
    images: list[UploadFile],
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest multiple images: save files, detect faces, and cluster into GrabIDs.
    """
    if not images:
        raise HTTPException(status_code=400, detail="No files provided")

    results: list[IngestResult] = []
    total_faces_found = 0

    for upload_file in images:
        # Validate content type
        if not upload_file.content_type or not upload_file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=422,
                detail=f"File '{upload_file.filename}' is not an image (content_type: {upload_file.content_type})",
            )

        try:
            # Save file to upload directory with UUID filename
            file_ext = Path(upload_file.filename or "image.jpg").suffix or ".jpg"
            file_id = uuid.uuid4()
            saved_filename = f"{file_id}{file_ext}"
            file_path = Path(settings.UPLOAD_DIR) / saved_filename

            content = await upload_file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            # Create Image record
            image = Image(
                id=file_id,
                file_path=str(file_path),
                original_filename=upload_file.filename or "unknown",
            )
            db.add(image)
            await db.flush()

            # Extract face embeddings
            embeddings = extract_embeddings(str(file_path))
            face_grab_ids: list[uuid.UUID] = []

            for face_data in embeddings:
                embedding = face_data["embedding"]
                facial_area = face_data["facial_area"]

                # Get or create a GrabID for this face
                grab_id = await get_or_create_grab_id(db, embedding)
                face_grab_ids.append(grab_id)

                # Create association record
                assoc = ImageGrabID(
                    image_id=image.id,
                    grab_id=grab_id,
                    face_area=facial_area,
                )
                db.add(assoc)

            await db.flush()

            faces_found = len(embeddings)
            total_faces_found += faces_found

            results.append(IngestResult(
                image_id=image.id,
                filename=upload_file.filename or "unknown",
                faces_found=faces_found,
                grab_ids=face_grab_ids,
            ))

        except HTTPException:
            raise
        except Exception as e:
            print(f"[ingest] Error processing file '{upload_file.filename}': {e}")
            # Continue processing other images
            continue

    await db.commit()

    return IngestResponse(
        ingested=results,
        total_images=len(results),
        total_faces_found=total_faces_found,
    )
