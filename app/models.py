import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class GrabID(Base):
    """Represents a unique face identity cluster."""
    __tablename__ = "grab_ids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    embedding = Column(JSON, nullable=False)  # list of 128 floats stored as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to images through ImageGrabID
    images = relationship("ImageGrabID", back_populates="grab_id_rel", lazy="selectin")


class Image(Base):
    """Represents an ingested photo."""
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to grab_ids through ImageGrabID
    grab_ids = relationship("ImageGrabID", back_populates="image_rel", lazy="selectin")


class ImageGrabID(Base):
    """Association table linking images to face identity clusters."""
    __tablename__ = "image_grab_ids"

    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), primary_key=True)
    grab_id = Column(UUID(as_uuid=True), ForeignKey("grab_ids.id"), primary_key=True)
    face_area = Column(JSON, nullable=True)  # {"x": int, "y": int, "w": int, "h": int}

    # Relationships
    image_rel = relationship("Image", back_populates="grab_ids")
    grab_id_rel = relationship("GrabID", back_populates="images")
