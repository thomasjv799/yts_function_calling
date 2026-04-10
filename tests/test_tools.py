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
