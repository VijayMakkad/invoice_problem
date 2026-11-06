import os
from pathlib import Path
from decimal import Decimal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_PATH: str = str(Path(__file__).parent.parent.parent / "data" / "invoiceiq.db")
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_TIMEOUT_SECONDS: float = 15.0
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5vl:3b"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0
    DEFAULT_TOLERANCE_PERCENT: Decimal = Decimal("0.02")
    ENABLE_GCS_BACKUP: bool = False
    GCS_BUCKET_NAME: str = ""
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024  # 20MB
    MAX_DOCUMENT_PAGES: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

