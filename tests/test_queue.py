import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_add_job_calls_session_add_and_commit():
    mock_job = MagicMock()
    mock_job.id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("db.queue.AsyncSessionLocal", return_value=mock_session):
        from db.queue import add_job
        await add_job("Inception", 2010, 1, "http://t.co/t.torrent", "1080p", "123456")
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_duplicate_returns_true_when_job_exists():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("db.queue.AsyncSessionLocal", return_value=mock_session):
        from db.queue import check_duplicate
        result = await check_duplicate("Inception", 2010)
        assert result is True


@pytest.mark.asyncio
async def test_check_duplicate_returns_false_when_no_job():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("db.queue.AsyncSessionLocal", return_value=mock_session):
        from db.queue import check_duplicate
        result = await check_duplicate("Unknown Movie", 2099)
        assert result is False
