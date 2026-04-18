from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config import settings

# Async engine using asyncpg
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Async session factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Declarative base for ORM models
Base = declarative_base()


async def init_db() -> None:
    """Initialize the database and create all tables."""
    async with engine.begin() as conn:
        # Create all tables from our models
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency that yields an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
