from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from services.recommender import recommend_similar, build_taste_profile, get_for_you_feed

router = APIRouter()


@router.get("/recommend/similar")
async def get_similar(
    movie_id: int = Query(..., description="TMDB movie ID"),
    title: str = Query("", description="Movie title (for display)")
):
    """
    TF-IDF based movie recommendations.
    Example: GET /api/recommend/similar?movie_id=550&title=Fight+Club
    """
    result = await recommend_similar(movie_id, title)
    return {
        "source_title": result.get("source_title"),
        "source_id": result.get("source_id"),
        "results": result.get("results", []),
        "count": len(result.get("results", [])),
        "ai_method": "TF-IDF cosine similarity on movie overviews",
    }


class WatchedPayload(BaseModel):
    watched: list[dict]


@router.post("/recommend/taste")
async def get_taste_profile(payload: WatchedPayload):
    """
    Builds user taste profile from watched list.
    POST /api/recommend/taste  body: { "watched": [...movies] }
    """
    if not payload.watched:
        raise HTTPException(status_code=400, detail="Watched list is empty")
    profile = build_taste_profile(payload.watched)
    return profile


@router.post("/recommend/foryou")
async def for_you(payload: WatchedPayload):
    """
    Personalized "For You" feed.
    POST /api/recommend/foryou  body: { "watched": [...movies] }
    """
    if not payload.watched:
        raise HTTPException(status_code=400, detail="Watched list is empty")
    results = await get_for_you_feed(payload.watched)
    return {"results": results, "count": len(results)}