import asyncio
from bot.client import bot
from db.queue import init_db
from config import Config


async def main() -> None:
    Config.validate()
    await init_db()
    async with bot:
        await bot.start(Config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
