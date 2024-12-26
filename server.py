from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from movie_search import search_movies, get_movie_details

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MovieSearchRequest(BaseModel):
    query: str
    quality: Optional[str] = None
    minimum_rating: Optional[float] = 0
    page: Optional[int] = 1
    limit: Optional[int] = 20


@app.post("/api/search")
async def search_movies_endpoint(request: MovieSearchRequest):
    movies = await search_movies(
        query=request.query,
        quality=request.quality,
        minimum_rating=request.minimum_rating,
        page=request.page,
        limit=request.limit,
    )

    if not movies:
        return {"status": "error", "message": "No movies found"}

    return {
        "status": "success",
        "data": [
            {
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "rating": movie.rating,
                "language": movie.language,
                "torrents": [
                    {
                        "url": t.url,
                        "quality": t.quality,
                        "type": t.type,
                        "size": t.size,
                        "seeds": t.seeds,
                        "peers": t.peers,
                    }
                    for t in movie.torrents
                ],
            }
            for movie in movies
        ],
    }


@app.get("/api/movie/{movie_id}")
async def get_movie_details_endpoint(movie_id: int):
    movie = await get_movie_details(movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return {"status": "success", "data": movie}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
