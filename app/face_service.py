"""
Face recognition service — embedding extraction, matching, and GrabID management.
Uses InsightFace (ArcFace model) for 512-dim embeddings and NumPy cosine similarity for matching.
"""

import uuid
from uuid import UUID

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import GrabID

# Initialize InsightFace model (loaded once at module level)
face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def extract_embeddings(image_path: str) -> list[dict]:
    """
    Extract face embeddings from an image using InsightFace.

    Args:
        image_path: Path to the image file.

    Returns:
        List of dicts, each with "embedding" (list of 512 floats) and "facial_area" (dict).
        Returns [] if no faces detected or on any error.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"[face_service] Could not read image: {image_path}")
            return []

        faces = face_app.get(img)
        embeddings = []
        for face in faces:
            bbox = face.bbox.astype(int)  # [x1, y1, x2, y2]
            x, y = int(bbox[0]), int(bbox[1])
            w, h = int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])
            embeddings.append({
                "embedding": face.embedding.tolist(),
                "facial_area": {"x": x, "y": y, "w": w, "h": h},
            })
        return embeddings
    except Exception as e:
        print(f"[face_service] Error extracting embeddings from {image_path}: {e}")
        return []


async def find_matching_grab_id(db: AsyncSession, embedding: list[float]) -> UUID | None:
    """
    Find an existing GrabID whose embedding is most similar to the given embedding,
    using NumPy cosine similarity.

    Args:
        db: Async database session.
        embedding: 512-dimensional face embedding vector.

    Returns:
        UUID of the matching GrabID if similarity > SIMILARITY_THRESHOLD, else None.
    """
    result = await db.execute(select(GrabID.id, GrabID.embedding))
    rows = result.all()

    if not rows:
        return None

    best_id = None
    best_score = -1.0

    for grab_id, stored_embedding in rows:
        score = cosine_similarity(embedding, stored_embedding)
        if score > best_score:
            best_score = score
            best_id = grab_id

    if best_score > settings.SIMILARITY_THRESHOLD:
        return best_id
    return None


async def get_or_create_grab_id(db: AsyncSession, embedding: list[float]) -> UUID:
    """
    Find a matching GrabID or create a new one.

    Args:
        db: Async database session.
        embedding: 512-dimensional face embedding vector.

    Returns:
        UUID of the matched or newly created GrabID.
    """
    existing_id = await find_matching_grab_id(db, embedding)
    if existing_id is not None:
        return existing_id

    # Create a new GrabID with this embedding
    new_grab_id = GrabID(
        id=uuid.uuid4(),
        embedding=embedding,
    )
    db.add(new_grab_id)
    await db.flush()
    return new_grab_id.id
