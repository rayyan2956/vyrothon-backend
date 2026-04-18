from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    DATABASE_URL: str = "postgresql+asyncpg://grabpic:grabpic_secret@localhost:5432/grabpic_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://grabpic:grabpic_secret@localhost:5432/grabpic_db"
    UPLOAD_DIR: str = "./uploads"
    SIMILARITY_THRESHOLD: float = 0.60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
