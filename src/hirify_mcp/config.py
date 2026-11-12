"""Centralized configuration and environment settings for Hirify MCP."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


class Settings:
    """Application settings loaded from environment variables with sensible defaults."""

    # Hirify API settings
    API_BASE_URL: str = os.getenv("HIRIFY_API_BASE_URL", "https://api.hirify.me/api").rstrip("/")
    REQUEST_TIMEOUT: float = float(os.getenv("HIRIFY_REQUEST_TIMEOUT", "15.0"))
    MAX_RETRIES: int = int(os.getenv("HIRIFY_MAX_RETRIES", "3"))
    RETRY_BACKOFF: float = float(os.getenv("HIRIFY_RETRY_BACKOFF", "0.5"))
    RATE_LIMIT_DELAY: float = float(os.getenv("HIRIFY_RATE_LIMIT_DELAY", "0.1"))
    MAX_PAGE_REQUESTS: int = int(os.getenv("HIRIFY_MAX_PAGE_REQUESTS", "5"))

    # Caching settings
    CACHE_ENABLED: bool = os.getenv("HIRIFY_CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
    CACHE_TTL: int = int(os.getenv("HIRIFY_CACHE_TTL", "300"))  # in seconds (5 minutes)

    # SQLite Storage settings
    DB_PATH: str = os.getenv("HIRIFY_DB_PATH", "hirify_history.db")

    # Logging settings
    LOG_LEVEL: str = os.getenv("HIRIFY_LOG_LEVEL", "INFO").upper()

    @classmethod
    def get_db_path(cls) -> Path:
        """Return resolved path to the SQLite database."""
        path = Path(cls.DB_PATH)
        if not path.is_absolute():
            # Place database relative to user data or current working directory
            path = Path.cwd() / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Configure logging to stderr to prevent interference with MCP stdio transport."""
    log_level = level or settings.LOG_LEVEL
    numeric_level = getattr(logging, log_level, logging.INFO)

    logger = logging.getLogger("hirify_mcp")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
