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
    WORKER_POLL_INTERVAL: int = int(os.getenv("WORKER_POLL_INTERVAL", "5"))

    @staticmethod
    def validate() -> None:
        required = ["GROQ_API_KEY", "DISCORD_BOT_TOKEN", "DISCORD_USER_ID", "DATABASE_URL"]
        missing = [k for k in required if not getattr(Config, k)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    @staticmethod
    def async_db_url() -> str:
        return Config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
