"""
MovieAI Intelligent Search Engine
----------------------------------
Multi-strategy search with:
1. Query understanding (intent detection, year/genre extraction)
2. Input normalization (typos, camelCase, smushed words, slang)
3. Multi-pass TMDB search (exact → fuzzy → keyword splits → partial)
4. Smart result ranking (relevance + popularity + rating)
5. Deduplication
"""

import re
import asyncio
from difflib import SequenceMatcher
from services.tmdb import search_movies_tmdb, normalize_movie, TMDB_API_KEY, BASE_URL
import httpx

# ─── Common movie slang / shorthand mappings ───────────────────────────────
ALIASES = {
    "avengers": "avengers",
    "batman v superman": "batman v superman dawn of justice",
    "bvs": "batman v superman",
    "tdk": "the dark knight",
    "lotr": "lord of the rings",
    "potc": "pirates of the caribbean",
    "httyd": "how to train your dragon",
    "tnmt": "teenage mutant ninja turtles",
    "f&f": "fast and furious",
    "fnf": "fast and furious",
    "fast furious": "fast and furious",
    "spiderman": "spider-man",
    "ironman": "iron man",
    "antman": "ant-man",
    "doctorstrange": "doctor strange",
    "guardiansofthegalaxy": "guardians of the galaxy",
    "gog": "guardians of the galaxy",
    "gotg": "guardians of the galaxy",
    "endgame": "avengers endgame",
    "infinitywar": "avengers infinity war",
    "johnwick": "john wick",
    "starwars": "star wars",
    "harrypotter": "harry potter",
    "lordoftherings": "lord of the rings",
    "darknight": "the dark knight",
    "darkknightrises": "the dark knight rises",
    "fightclub": "fight club",
    "pulpfiction": "pulp fiction",
    "forrestgump": "forrest gump",
    "schindlerslist": "schindler's list",
    "goodfellas": "goodfellas",
    "silenceofthelambs": "silence of the lambs",
    "thesilenceofthelambs": "the silence of the lambs",
    "nolansfilm": "christopher nolan",
    "tarantino": "quentin tarantino",
}

# ─── Levenshtein-style similarity ──────────────────────────────────────────
def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ─── Query normalizer ───────────────────────────────────────────────────────
def normalize_query(raw: str) -> dict:
    """
    Returns structured query info:
    {
      "cleaned": "john wick",
      "year": "2014" or None,
      "is_smushed": True/False,
    }
    """
    q = raw.strip()

    # Extract year if present: "inception 2010" or "2010 inception"
    year_match = re.search(r'\b(19|20)\d{2}\b', q)
    year = year_match.group(0) if year_match else None
    if year:
        q = q.replace(year, "").strip()

    # Lowercase for alias check
    q_lower = q.lower().replace(" ", "")

    # Check aliases first
    if q_lower in ALIASES:
        q = ALIASES[q_lower]
        return {"cleaned": q, "year": year, "is_smushed": False}

    # Also check with spaces removed
    q_nospace = re.sub(r'\s+', '', q.lower())
    if q_nospace in ALIASES:
        q = ALIASES[q_nospace]
        return {"cleaned": q, "year": year, "is_smushed": False}

    # Replace separators
    q = q.replace("_", " ").replace("-", " ")

    # camelCase split: "JohnWick" → "John Wick"
    if " " not in q and any(c.isupper() for c in q[1:]):
        q = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', q)

    # Collapse spaces
    q = " ".join(q.split())

    is_smushed = " " not in q and len(q) > 5

    return {"cleaned": q, "year": year, "is_smushed": is_smushed}


# ─── Generate search candidates ────────────────────────────────────────────
def generate_candidates(query_info: dict) -> list[str]:
    """
    Generates multiple query variants to try against TMDB.
    Returns ordered list from most → least specific.
    """
    cleaned = query_info["cleaned"]
    year = query_info["year"]
    candidates = []

    # 1. Exact cleaned query
    candidates.append(cleaned)

    # 2. With year appended if available
    if year:
        candidates.append(f"{cleaned} {year}")

    # 3. If smushed (no spaces), try all split positions
    if query_info["is_smushed"] and len(cleaned) > 4:
        for i in range(2, len(cleaned) - 1):
            candidates.append(cleaned[:i] + " " + cleaned[i:])

    # 4. Drop articles: "the dark knight" → "dark knight"
    articles = ["the ", "a ", "an "]
    for art in articles:
        if cleaned.lower().startswith(art):
            candidates.append(cleaned[len(art):])

    # 5. First word only (for short/partial queries)
    words = cleaned.split()
    if len(words) > 2:
        candidates.append(words[0])
        candidates.append(" ".join(words[:2]))

    # Deduplicate preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c.lower() not in seen and c.strip():
            seen.add(c.lower())
            unique.append(c)

    return unique


# ─── Smart result ranker ────────────────────────────────────────────────────
def rank_results(results: list, original_query: str) -> list:
    """
    Re-ranks TMDB results by combining:
    - Title similarity to query (most important)
    - Popularity score from TMDB
    - Vote average (rating)
    - Vote count (avoid obscure low-vote movies ranking high)
    """
    query_lower = original_query.lower().strip()

    def score(movie):
        title = (movie.get("title") or "").lower()
        orig_title = (movie.get("original_title") or "").lower()

        # Title match score (0–1)
        title_sim = max(
            similarity(query_lower, title),
            similarity(query_lower, orig_title),
        )

        # Exact match bonus
        exact_bonus = 1.5 if title == query_lower else 0

        # Starts-with bonus
        starts_bonus = 0.3 if title.startswith(query_lower) else 0

        # Popularity (TMDB score, normalize to ~0–1 range assuming max ~5000)
        popularity = min(movie.get("popularity", 0) / 500, 1.0)

        # Rating (0–10 scale → 0–1)
        rating = movie.get("vote_average", 0) / 10

        # Vote count trust factor (penalize movies with < 50 votes)
        vote_count = movie.get("vote_count", 0)
        trust = min(vote_count / 200, 1.0)

        final = (title_sim * 4) + exact_bonus + starts_bonus + (popularity * 2) + (rating * trust)
        return final

    return sorted(results, key=score, reverse=True)


# ─── Deduplicator ──────────────────────────────────────────────────────────
def deduplicate(results: list) -> list:
    seen_ids = set()
    unique = []
    for r in results:
        rid = r.get("id")
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            unique.append(r)
    return unique


# ─── Multi-strategy search: fetch by genre/person via TMDB ─────────────────
async def search_by_person(name: str) -> list:
    """Search movies by director/actor name."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Search for person
            pr = await client.get(
                f"{BASE_URL}/search/person",
                params={"api_key": TMDB_API_KEY, "query": name}
            )
            pr.raise_for_status()
            people = pr.json().get("results", [])
            if not people:
                return []

            person = people[0]
            person_id = person["id"]

            # Get their movie credits
            cr = await client.get(
                f"{BASE_URL}/person/{person_id}/movie_credits",
                params={"api_key": TMDB_API_KEY}
            )
            cr.raise_for_status()
            credits = cr.json()
            movies = credits.get("cast", []) + credits.get("crew", [])
            # Sort by popularity
            movies = sorted(movies, key=lambda m: m.get("popularity", 0), reverse=True)
            return movies[:20]
    except Exception as e:
        print(f"Person search error: {e}")
        return []


# ─── MAIN INTELLIGENT SEARCH FUNCTION ──────────────────────────────────────
async def intelligent_search(raw_query: str) -> dict:
    """
    Full intelligent search pipeline.
    Returns: { "results": [...], "query_used": "...", "strategy": "..." }
    """
    query_info = normalize_query(raw_query)
    cleaned = query_info["cleaned"]
    candidates = generate_candidates(query_info)

    all_results = []
    strategy_used = "direct"
    query_used = cleaned

    # --- Strategy 1: Try all generated candidates in parallel ---
    search_tasks = [search_movies_tmdb(c) for c in candidates[:6]]  # limit parallel calls
    batch_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    for i, res in enumerate(batch_results):
        if isinstance(res, list) and res:
            all_results.extend(res)
            query_used = candidates[i]
            if i == 0:
                strategy_used = "direct"
            elif i == 1 and query_info["year"]:
                strategy_used = "with_year"
            else:
                strategy_used = "fuzzy_split"

    # --- Strategy 2: If still nothing, try person search ---
    if not all_results and len(cleaned.split()) <= 2:
        person_results = await search_by_person(cleaned)
        if person_results:
            all_results = person_results
            strategy_used = "person_search"

    # --- Strategy 3: Last resort — search each word individually ---
    if not all_results:
        words = [w for w in cleaned.split() if len(w) > 3]
        for word in words[:3]:
            res = await search_movies_tmdb(word)
            if res:
                all_results.extend(res)
                strategy_used = "keyword_fallback"
                break

    if not all_results:
        return {"results": [], "query_used": cleaned, "strategy": "no_results"}

    # Deduplicate and rank
    all_results = deduplicate(all_results)
    all_results = rank_results(all_results, cleaned)

    # Normalize for frontend
    normalized = [normalize_movie(m) for m in all_results[:12]]

    return {
        "results": normalized,
        "query_used": query_used,
        "strategy": strategy_used,
        "total_found": len(all_results),
    }