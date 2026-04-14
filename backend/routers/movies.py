from fastapi import APIRouter, HTTPException
from services.tmdb import fetch_movie_details, fetch_trending_movies, normalize_movie

router = APIRouter()


@router.get("/movies/trending")
async def get_trending():
    """
    Get trending movies this week.
    Example: GET /api/movies/trending
    """
    results = await fetch_trending_movies()
    if not results:
        return {"results": [], "count": 0}
    movies = [normalize_movie(m) for m in results[:12]]
    return {"results": movies, "count": len(movies)}


@router.get("/movies/{movie_id}")
async def get_movie(movie_id: int):
    """
    Get full details for a specific movie.
    Example: GET /api/movies/550
    """
    movie = await fetch_movie_details(movie_id)
    if not movie or movie.get("success") is False:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie