# downloader/subtitles.py
import asyncio
import logging
from config import Config

logger = logging.getLogger(__name__)


async def download_subtitles(file_path: str, movie_title: str, movie_year: int) -> bool:
    """Download English subtitles for file_path using subliminal.

    Skipped if OPENSUBTITLES_USERNAME / OPENSUBTITLES_PASSWORD are not set.
    Returns True if subtitles were saved. Failures are logged but never raised —
    subtitle download is best-effort and should not block the download completion flow.
    """
    if not Config.OPENSUBTITLES_USERNAME or not Config.OPENSUBTITLES_PASSWORD:
        logger.info("Subtitle download skipped — OpenSubtitles credentials not configured.")
        return False

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_sync, file_path)


def _download_sync(file_path: str) -> bool:
    try:
        import subliminal
        from babelfish import Language

        video = subliminal.scan_video(file_path)
        subtitles = subliminal.download_best_subtitles([video], {Language("eng")})
        if subtitles.get(video):
            subliminal.save_subtitles(video, subtitles[video])
            logger.info("Subtitles saved for %s", file_path)
            return True
        logger.info("No subtitles found for %s", file_path)
        return False
    except Exception as exc:
        logger.warning("Subtitle download failed for %s: %s", file_path, exc)
        return False
