"""Run once to initialize the PostgreSQL database schema."""
import asyncio
from db.queue import init_db
from config import Config


async def main() -> None:
    Config.validate()
    await init_db()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
