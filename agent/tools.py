from typing import Optional
import httpx
from langchain_core.tools import tool

YTS_BASE = "https://yts.mx/api/v2"


@tool
async def search_movies(query: str, quality: Optional[str] = None, minimum_rating: float = 0) -> str:
    """Search for movies on YTS by title. Returns up to 5 matches with IDs, years, and ratings."""
    params: dict = {"query_term": query, "limit": 5, "with_rt_ratings": "true"}
    if quality:
        params["quality"] = quality
    if minimum_rating > 0:
        params["minimum_rating"] = minimum_rating

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{YTS_BASE}/list_movies.json", params=params)
        data = resp.json()

    if data["status"] != "ok" or not data["data"].get("movie_count"):
        return "No movies found."

    lines = []
    for m in data["data"]["movies"][:5]:
        qualities = [t["quality"] for t in m.get("torrents", [])]
        lines.append(
            f"ID:{m['id']} | {m['title']} ({m['year']}) | "
            f"Rating: {m['rating']} | Available: {', '.join(qualities)}"
        )
    return "\n".join(lines)


@tool
async def get_movie_details(movie_id: int) -> str:
    """Get full details for a movie: synopsis, rating, and available torrents with seeds and size."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{YTS_BASE}/movie_details.json",
            params={"movie_id": movie_id, "with_images": True, "with_cast": True},
        )
        data = resp.json()

    if data["status"] != "ok":
        return "Movie not found."

    m = data["data"]["movie"]
    torrent_lines = [
        f"  {t['quality']} {t['type']} | {t['size']} | Seeds: {t['seeds']} | {t['url']}"
        for t in m.get("torrents", [])
    ]
    synopsis = m.get("description_full", "N/A")[:300]
    return (
        f"{m['title']} ({m['year']}) — ★{m['rating']}\n"
        f"{synopsis}\n"
        f"Poster: {m.get('large_cover_image', '')}\n"
        f"Torrents:\n" + "\n".join(torrent_lines)
    )


async def get_poster_url(movie_id: int) -> str:
    """Fetch the large cover image URL for a movie. Used for Discord notifications."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{YTS_BASE}/movie_details.json",
            params={"movie_id": movie_id, "with_images": True},
        )
        data = resp.json()
    if data["status"] != "ok":
        return ""
    return data["data"]["movie"].get("large_cover_image", "")
