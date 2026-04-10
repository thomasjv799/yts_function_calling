import asyncio
import logging
from bot.client import bot
from db.queue import init_db
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    Config.validate()
    logger.info("Config validated.")
    await init_db()
    logger.info("Database ready.")
    async with bot:
        await bot.start(Config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
