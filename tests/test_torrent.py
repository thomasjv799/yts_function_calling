import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_download_torrent_returns_largest_file_path(tmp_path):
    mock_files = MagicMock()
    mock_files.num_files.return_value = 2

    def file_path_impl(idx):
        return {0: "subs/sub.srt", 1: "Inception (2010).mkv"}[idx]

    def file_size_impl(idx):
        return {0: 10_000, 1: 2_000_000_000}[idx]

    mock_files.file_path.side_effect = file_path_impl
    mock_files.file_size.side_effect = file_size_impl

    mock_info = MagicMock()
    mock_info.files.return_value = mock_files

    mock_handle = MagicMock()
    mock_handle.is_seed.side_effect = [False, True]
    mock_handle.get_torrent_info.return_value = mock_info
    mock_status = MagicMock()
    mock_status.progress = 1.0
    mock_status.download_rate = 1024 * 1024
    mock_handle.status.return_value = mock_status

    mock_session = MagicMock()
    mock_session.add_torrent.return_value = mock_handle

    progress_calls = []

    async def on_progress(pct, speed):
        progress_calls.append((pct, speed))

    mock_lt = MagicMock()
    mock_lt.session.return_value = mock_session
    mock_lt.add_torrent_params.return_value = MagicMock()

    with patch("downloader.torrent.lt", mock_lt):
        from downloader.torrent import download_torrent
        result = await download_torrent(
            "http://example.com/inception.torrent",
            str(tmp_path),
            on_progress,
        )

    assert result.endswith("Inception (2010).mkv")
    assert len(progress_calls) >= 1
