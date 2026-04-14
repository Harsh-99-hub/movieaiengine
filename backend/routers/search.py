from fastapi import APIRouter, Query, HTTPException
from services.search_engine import intelligent_search

router = APIRouter()


@router.get("/search")
async def search_movies(q: str = Query(..., min_length=1, description="Movie title to search")):
    """
    Intelligent movie search.
    Handles: typos, smushed words, camelCase, slang, aliases,
             year hints, director/actor names, partial titles.
    Example: GET /api/search?q=johnwick
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = await intelligent_search(q.strip())

    return {
        "query": q,
        "query_interpreted": result["query_used"],
        "strategy": result["strategy"],
        "results": result["results"],
        "count": len(result["results"]),
    }