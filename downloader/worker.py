import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from db.queue import get_pending_job, update_job
from db.models import DownloadJob
from downloader.torrent import download_torrent
from downloader.subtitles import download_subtitles
from config import Config


async def run_worker(notify_callback: Callable) -> None:
    """Poll the download queue indefinitely and process jobs as they arrive."""
    while True:
        job = await get_pending_job()
        if job:
            await process_job(job, notify_callback)
        await asyncio.sleep(Config.WORKER_POLL_INTERVAL)


async def process_job(job: DownloadJob, notify_callback: Callable) -> None:
    """Download one job, rename to Plex structure, download subtitles, and notify."""
    await update_job(job.id, status="downloading")

    tmp_dir = os.path.join(Config.DOWNLOAD_PATH, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    async def on_progress(pct: float, speed: str) -> None:
        await update_job(job.id, progress=pct, speed=speed)

    try:
        raw_path = await download_torrent(job.torrent_url, tmp_dir, on_progress)

        final_dir = Path(Config.DOWNLOAD_PATH) / f"{job.movie_title} ({job.movie_year})"
        final_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(raw_path).suffix
        final_path = str(final_dir / f"{job.movie_title} ({job.movie_year}){ext}")
        os.rename(raw_path, final_path)

        await download_subtitles(final_path, job.movie_title, job.movie_year)

        await update_job(
            job.id,
            status="done",
            file_path=final_path,
            progress=100.0,
            speed="",
            completed_at=datetime.now(timezone.utc),
        )
        await notify_callback(job, final_path)

    except Exception as exc:
        await update_job(job.id, status="failed", error=str(exc))
        await notify_callback(job, None, error=str(exc))
