import httpx
import os

# ✅ Put your TMDB API key here
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "234bbd37cf600193b753ba996311fd7c")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def normalize_movie(movie: dict) -> dict:
    """Converts raw TMDB movie data into clean format."""
    poster_path = movie.get("poster_path")
    return {
        "id": movie.get("id"),
        "title": movie.get("title", "Unknown Title"),
        "overview": movie.get("overview", "No description available."),
        "poster": f"{IMAGE_BASE}{poster_path}" if poster_path else None,
        "rating": round(movie.get("vote_average", 0), 1),
        "release_year": (movie.get("release_date") or "")[:4],
        "genre_ids": movie.get("genre_ids", []),
    }


async def search_movies_tmdb(query: str) -> list:
    """Search movies by query string."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/search/movie",
                params={"api_key": TMDB_API_KEY, "query": query, "language": "en-US"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
    except httpx.HTTPStatusError as e:
        print(f"TMDB HTTP error: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"TMDB error: {e}")
        return []


async def fetch_movie_details(movie_id: int) -> dict:
    """Fetch full details for a single movie."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/movie/{movie_id}",
                params={"api_key": TMDB_API_KEY, "language": "en-US"},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching movie {movie_id}: {e}")
        return {}


async def fetch_trending_movies() -> list:
    """Fetch trending movies of the week."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/trending/movie/week",
                params={"api_key": TMDB_API_KEY},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
    except Exception as e:
        print(f"Error fetching trending: {e}")
        return []