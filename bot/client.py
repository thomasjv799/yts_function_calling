# bot/client.py
import asyncio
import logging
import discord
from bot.handlers import handle_message, send_completion_notification, send_failure_notification
from db.models import DownloadJob
from config import Config

logger = logging.getLogger(__name__)


class MovieBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._worker_task: asyncio.Task | None = None

    async def setup_hook(self) -> None:
        from downloader.worker import run_worker
        logger.info("Starting download worker...")
        self._worker_task = self.loop.create_task(run_worker(self._notify))
        self._worker_task.add_done_callback(self._worker_crashed)

    def _worker_crashed(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.critical("Download worker crashed: %s", exc, exc_info=exc)

    async def on_ready(self) -> None:
        logger.info("Bot ready as %s (ID: %s)", self.user, self.user.id)

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        if isinstance(message.channel, discord.DMChannel):
            await handle_message(message)

    async def _notify(
        self, job: DownloadJob, file_path: str | None, error: str | None = None
    ) -> None:
        try:
            if error:
                await send_failure_notification(
                    self, job.discord_user_id, job.movie_title, job.movie_year, error
                )
            else:
                await send_completion_notification(
                    self, job.discord_user_id, job.movie_title, job.movie_year, job.movie_id, file_path
                )
        except Exception:
            logger.exception("Failed to send notification for job %s", job.id)


bot = MovieBot()
