"""
Face recognition service — embedding extraction, matching, and GrabID management.
Uses DeepFace (Facenet model) for embeddings and NumPy cosine similarity for matching.
"""

import uuid
from uuid import UUID

import numpy as np
from deepface import DeepFace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import GrabID


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def extract_embeddings(image_path: str) -> list[dict]:
    """
    Extract face embeddings from an image using DeepFace.

    Args:
        image_path: Path to the image file.

    Returns:
        List of dicts, each with "embedding" (list[float]) and "facial_area" (dict).
        Returns [] if no faces detected or on any error.
    """
    try:
        results = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet",
            enforce_detection=False,
            detector_backend="opencv",
        )
        # DeepFace returns a list of dicts with "embedding" and "facial_area" keys
        embeddings = []
        for face in results:
            embeddings.append({
                "embedding": face["embedding"],
                "facial_area": face["facial_area"],
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
        embedding: 128-dimensional face embedding vector.

    Returns:
        UUID of the matching GrabID if similarity > 0.60, else None.
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
        embedding: 128-dimensional face embedding vector.

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
