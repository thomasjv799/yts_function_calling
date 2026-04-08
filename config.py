import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_USER_ID: str = os.getenv("DISCORD_USER_ID", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DOWNLOAD_PATH: str = os.getenv("DOWNLOAD_PATH", "./downloads")
    OPENSUBTITLES_USERNAME: str = os.getenv("OPENSUBTITLES_USERNAME", "")
    OPENSUBTITLES_PASSWORD: str = os.getenv("OPENSUBTITLES_PASSWORD", "")

    # Fix 1: Safe parsing of WORKER_POLL_INTERVAL
    _raw_poll = os.getenv("WORKER_POLL_INTERVAL", "5")
    try:
        WORKER_POLL_INTERVAL: int = int(_raw_poll)
    except ValueError:
        raise ValueError(
            f"WORKER_POLL_INTERVAL must be an integer, got: {_raw_poll!r}"
        )

    @staticmethod
    def validate() -> None:
        required = ["GROQ_API_KEY", "DISCORD_BOT_TOKEN", "DISCORD_USER_ID", "DATABASE_URL"]
        missing = [k for k in required if not getattr(Config, k)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    @staticmethod
    def async_db_url() -> str:
        # Fix 2: Guard against empty DATABASE_URL and handle postgres:// alias
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set; call Config.validate() first")
        url = Config.DATABASE_URL
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://"):]
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
