import pytest
import respx
import httpx

YTS_LIST_URL = "https://yts.mx/api/v2/list_movies.json"
YTS_DETAIL_URL = "https://yts.mx/api/v2/movie_details.json"


@pytest.mark.asyncio
@respx.mock
async def test_search_movies_returns_formatted_results():
    respx.get(YTS_LIST_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {
            "movie_count": 1,
            "movies": [{
                "id": 1,
                "title": "Inception",
                "year": 2010,
                "rating": 8.8,
                "torrents": [{"quality": "1080p"}],
            }],
        },
    }))
    from agent.tools import search_movies
    result = await search_movies.ainvoke({"query": "Inception"})
    assert "Inception" in result
    assert "2010" in result
    assert "8.8" in result


@pytest.mark.asyncio
@respx.mock
async def test_search_movies_returns_no_results_message():
    respx.get(YTS_LIST_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {"movie_count": 0},
    }))
    from agent.tools import search_movies
    result = await search_movies.ainvoke({"query": "xyznotamovie"})
    assert "No movies found" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_movie_details_returns_synopsis_and_torrents():
    respx.get(YTS_DETAIL_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {
            "movie": {
                "id": 1,
                "title": "Inception",
                "year": 2010,
                "rating": 8.8,
                "description_full": "A thief who steals corporate secrets.",
                "large_cover_image": "https://img.yts.mx/inception.jpg",
                "torrents": [
                    {"quality": "1080p", "type": "bluray", "size": "2.1 GB",
                     "seeds": 142, "url": "http://t.co/inception.torrent"},
                ],
            }
        },
    }))
    from agent.tools import get_movie_details
    result = await get_movie_details.ainvoke({"movie_id": 1})
    assert "Inception" in result
    assert "A thief" in result
    assert "1080p" in result
    assert "142" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_poster_url_returns_image_url():
    respx.get(YTS_DETAIL_URL).mock(return_value=httpx.Response(200, json={
        "status": "ok",
        "data": {"movie": {"large_cover_image": "https://img.yts.mx/inception.jpg"}},
    }))
    from agent.tools import get_poster_url
    url = await get_poster_url(1)
    assert url == "https://img.yts.mx/inception.jpg"


import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_check_duplicate_tool_returns_already_queued():
    with patch("db.queue.check_duplicate", new=AsyncMock(return_value=True)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        check_dup = next(t for t in tools if t.name == "check_duplicate")
        result = await check_dup.ainvoke({"movie_title": "Inception", "movie_year": 2010})
        assert "already" in result.lower()


@pytest.mark.asyncio
async def test_check_duplicate_tool_returns_not_in_queue():
    with patch("db.queue.check_duplicate", new=AsyncMock(return_value=False)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        check_dup = next(t for t in tools if t.name == "check_duplicate")
        result = await check_dup.ainvoke({"movie_title": "Unknown", "movie_year": 2020})
        assert "not in" in result.lower()


@pytest.mark.asyncio
async def test_queue_download_tool_calls_add_job():
    mock_job = MagicMock()
    mock_job.id = uuid.uuid4()
    with patch("db.queue.add_job", new=AsyncMock(return_value=mock_job)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        queue_dl = next(t for t in tools if t.name == "queue_download")
        result = await queue_dl.ainvoke({
            "movie_title": "Inception",
            "movie_year": 2010,
            "movie_id": 1,
            "torrent_url": "http://t.co/t.torrent",
            "quality": "1080p",
        })
        assert "Queued" in result
        assert "Inception" in result


@pytest.mark.asyncio
async def test_cancel_download_tool_returns_cancelled():
    with patch("db.queue.cancel_job_by_title", new=AsyncMock(return_value=True)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        cancel = next(t for t in tools if t.name == "cancel_download")
        result = await cancel.ainvoke({"movie_title": "Inception"})
        assert "Cancelled" in result


@pytest.mark.asyncio
async def test_cancel_download_tool_returns_not_found():
    with patch("db.queue.cancel_job_by_title", new=AsyncMock(return_value=False)):
        from agent.tools import build_queue_tools
        tools = build_queue_tools("123456")
        cancel = next(t for t in tools if t.name == "cancel_download")
        result = await cancel.ainvoke({"movie_title": "Unknown"})
        assert "No pending" in result
