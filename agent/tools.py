import os
from typing import Optional
import httpx
from langchain_core.tools import tool

YTS_BASE = os.getenv("YTS_BASE_URL", "https://yts.mx/api/v2").rstrip("/")


@tool
async def search_movies(query: str, quality: Optional[str] = None, minimum_rating: float = 0) -> str:
    """Search for movies on YTS by title. Returns up to 5 matches with IDs, years, and ratings."""
    params: dict = {"query_term": query, "limit": 5, "with_rt_ratings": "true"}
    if quality:
        params["quality"] = quality
    if minimum_rating > 0:
        params["minimum_rating"] = minimum_rating

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        resp = await client.get(
            f"{YTS_BASE}/movie_details.json",
            params={"movie_id": movie_id, "with_images": True, "with_cast": True},
        )
        data = resp.json()

    if data["status"] != "ok":
        return "Movie not found."

    m = data["data"]["movie"]
    torrent_lines = [
        f"  {t.get('quality', '?')} {t.get('type', '?')} | {t.get('size', 'Unknown')} | Seeds: {t.get('seeds', 0)} | {t.get('url', '')}"
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        resp = await client.get(
            f"{YTS_BASE}/movie_details.json",
            params={"movie_id": movie_id, "with_images": True},
        )
        data = resp.json()
    if data["status"] != "ok":
        return ""
    return data["data"]["movie"].get("large_cover_image", "")


from db import queue as db_queue


def build_queue_tools(discord_user_id: str) -> list:
    """Create queue management tools with discord_user_id baked into queue_download."""

    @tool
    async def check_duplicate(movie_title: str, movie_year: int) -> str:
        """Check if a movie is already downloaded or in the download queue."""
        exists = await db_queue.check_duplicate(movie_title, movie_year)
        if exists:
            return f"{movie_title} ({movie_year}) is already in the queue or downloaded."
        return f"{movie_title} ({movie_year}) is not in the queue."

    @tool
    async def queue_download(
        movie_title: str, movie_year: int, movie_id: int, torrent_url: str, quality: str
    ) -> str:
        """Queue a movie for download after the user has confirmed."""
        job = await db_queue.add_job(
            movie_title, movie_year, movie_id, torrent_url, quality, discord_user_id
        )
        return f"Queued {movie_title} ({movie_year}) [{quality}]. Job ID: {job.id}"

    @tool
    async def get_queue_status() -> str:
        """Get the current status of all downloads (downloading, pending, done, failed)."""
        jobs = await db_queue.get_all_jobs()
        if not jobs:
            return "No downloads in queue."
        status_map = {
            "downloading": lambda j: f"⏬ {j.movie_title} ({j.movie_year}) — {j.progress:.0f}% at {j.speed}",
            "pending": lambda j: f"⏳ {j.movie_title} ({j.movie_year}) — pending",
            "done": lambda j: f"✅ {j.movie_title} ({j.movie_year}) — done",
            "failed": lambda j: f"❌ {j.movie_title} ({j.movie_year}) — failed: {j.error}",
            "cancelled": lambda j: f"🚫 {j.movie_title} ({j.movie_year}) — cancelled",
        }
        lines = [status_map.get(j.status, lambda j: f"? {j.movie_title}")(j) for j in jobs]
        return "\n".join(lines)

    @tool
    async def cancel_download(movie_title: str) -> str:
        """Cancel a pending download by movie title."""
        success = await db_queue.cancel_job_by_title(movie_title)
        if success:
            return f"Cancelled download for {movie_title}."
        return f"No pending download found for {movie_title}."

    return [check_duplicate, queue_download, get_queue_status, cancel_download]
