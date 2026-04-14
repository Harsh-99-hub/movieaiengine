from fastapi import APIRouter, Query, HTTPException
from services.vibe_engine import vibe_search

router = APIRouter()


@router.get("/vibe")
async def vibe_search_endpoint(q: str = Query(..., min_length=3, description="Natural language vibe query")):
    """
    AI vibe-based movie search using NLP + cosine similarity.

    Examples:
      GET /api/vibe?q=less complicated than Interstellar
      GET /api/vibe?q=darker than John Wick
      GET /api/vibe?q=something feel-good
      GET /api/vibe?q=like Inception but funnier
      GET /api/vibe?q=simpler than Tenet
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = await vibe_search(q.strip())
    return {
        "query": q,
        "reference_movie": result.get("reference_movie"),
        "parsed_intent": result.get("parsed_intent"),
        "target_profile": result.get("target_profile"),
        "results": result.get("results", []),
        "count": len(result.get("results", [])),
    }