# movie_search.py
import httpx
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class MovieTorrent:
    url: str
    quality: str
    type: str
    seeds: int
    peers: int
    size: str
    hash: str


@dataclass
class MovieResult:
    id: int
    title: str
    year: int
    rating: float
    language: str
    torrents: List[MovieTorrent]


async def search_movies(
    query: str,
    quality: Optional[str] = None,
    minimum_rating: float = 0,
    with_rt_ratings: bool = True,
    page: int = 1,
    limit: int = 20,
) -> List[MovieResult]:
    """
    Search for movies using the YTS API.
    """
    base_url = "https://yts.mx/api/v2"

    params = {
        "query_term": query,
        "page": page,
        "limit": limit,
        "with_rt_ratings": str(with_rt_ratings).lower(),
    }

    if quality:
        params["quality"] = quality
    if minimum_rating > 0:
        params["minimum_rating"] = minimum_rating

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/list_movies.json", params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] != "ok":
                print(f"API Error: {data.get('status_message')}")
                return []

            if not data["data"]["movie_count"]:
                return []

            movies = []
            for movie_data in data["data"]["movies"]:
                torrents = [
                    MovieTorrent(
                        url=t["url"],
                        quality=t["quality"],
                        type=t["type"],
                        seeds=t["seeds"],
                        peers=t["peers"],
                        size=t["size"],
                        hash=t["hash"],
                    )
                    for t in movie_data.get("torrents", [])
                ]

                movie = MovieResult(
                    id=movie_data["id"],
                    title=movie_data["title"],
                    year=movie_data["year"],
                    rating=movie_data["rating"],
                    language=movie_data["language"],
                    torrents=torrents,
                )
                movies.append(movie)

            return movies

        except Exception as e:
            print(f"Error searching movies: {str(e)}")
            return []


async def get_movie_details(movie_id: int) -> Optional[Dict]:
    """
    Get detailed information about a specific movie.
    """
    base_url = "https://yts.mx/api/v2"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/movie_details.json",
                params={"movie_id": movie_id, "with_images": True, "with_cast": True},
            )
            response.raise_for_status()
            data = response.json()

            if data["status"] != "ok":
                return None

            return data["data"]["movie"]

        except Exception as e:
            print(f"Error fetching movie details: {str(e)}")
            return None
