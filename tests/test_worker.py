import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def make_mock_job():
    job = MagicMock()
    job.id = uuid.uuid4()
    job.movie_title = "Inception"
    job.movie_year = 2010
    job.movie_id = 1
    job.torrent_url = "http://example.com/inception.torrent"
    job.quality = "1080p"
    job.discord_user_id = "123456"
    return job


@pytest.mark.asyncio
async def test_process_job_marks_done_and_calls_notify(tmp_path):
    job = make_mock_job()
    fake_file = tmp_path / "Inception.mkv"
    fake_file.write_text("fake")

    notify_calls = []

    async def mock_notify(j, path, error=None):
        notify_calls.append((j, path, error))

    with patch("downloader.worker.update_job", new=AsyncMock()), \
         patch("downloader.worker.download_torrent", new=AsyncMock(return_value=str(fake_file))), \
         patch("downloader.worker.download_subtitles", new=AsyncMock()), \
         patch("downloader.worker.Config") as mock_cfg, \
         patch("os.makedirs"), \
         patch("os.rename"):
        mock_cfg.DOWNLOAD_PATH = str(tmp_path)
        mock_cfg.WORKER_POLL_INTERVAL = 0

        from downloader.worker import process_job
        await process_job(job, mock_notify)

    assert len(notify_calls) == 1
    called_job, called_path, called_error = notify_calls[0]
    assert called_error is None
    assert called_job is job


@pytest.mark.asyncio
async def test_process_job_marks_failed_and_notifies_on_error():
    job = make_mock_job()
    notify_calls = []

    async def mock_notify(j, path, error=None):
        notify_calls.append((j, path, error))

    with patch("downloader.worker.update_job", new=AsyncMock()), \
         patch("downloader.worker.download_torrent", new=AsyncMock(side_effect=RuntimeError("no peers"))), \
         patch("downloader.worker.download_subtitles", new=AsyncMock()), \
         patch("downloader.worker.Config") as mock_cfg, \
         patch("os.makedirs"):
        mock_cfg.DOWNLOAD_PATH = "/tmp/movies"
        mock_cfg.WORKER_POLL_INTERVAL = 0

        from downloader.worker import process_job
        await process_job(job, mock_notify)

    assert len(notify_calls) == 1
    assert notify_calls[0][2] == "no peers"
