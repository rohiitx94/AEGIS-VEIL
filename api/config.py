"""
API Configuration — Environment Variables & Settings
=====================================================
Central configuration for the FastAPI backend.
Uses python-dotenv to load from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # ── Server ──
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ── Paths ──
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    UPLOAD_DIR: Path = PROJECT_ROOT / "storage" / "uploads"
    STEGO_DIR: Path = PROJECT_ROOT / "storage" / "stego_images"
    CARRIER_DIR: Path = PROJECT_ROOT / "storage" / "carriers"
    EXTRACTED_DIR: Path = PROJECT_ROOT / "storage" / "extracted"

    # ── API Keys ──
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ── Auth & Security ──
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-for-stego-cloud")
    GALLERY_PASSWORD: str = os.getenv("GALLERY_PASSWORD", "impact123")
    PANIC_PASSWORD: str = os.getenv("PANIC_PASSWORD", "chutiyehokya")
    
    # ── Database ──
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # ── Limits ──
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
    MAX_CARRIER_RESOLUTION: int = int(os.getenv("MAX_CARRIER_RESOLUTION", "8294400"))  # 4K = 3840*2160

    # ── CORS ──
    CORS_ORIGINS: list = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]

    def __init__(self):
        """Create required directories on init."""
        for directory in [self.UPLOAD_DIR, self.STEGO_DIR, self.CARRIER_DIR, self.EXTRACTED_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

        # Set Gemini API key in environment if provided
        if self.GEMINI_API_KEY:
            os.environ["GEMINI_API_KEY"] = self.GEMINI_API_KEY


settings = Settings()
