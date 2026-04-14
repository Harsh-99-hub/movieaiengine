"""
MovieAI Recommendation Engine
-------------------------------
Two AI techniques:

1. TF-IDF + Cosine Similarity on movie overviews
   - Builds term-frequency vectors from movie descriptions
   - Finds movies with the most similar text content
   - Same technique used in real search engines & RecSys

2. Taste Profile Builder
   - Aggregates genre + vibe dimension scores from watched movies
   - Produces a user "fingerprint" of what they like
   - Used to power the "For You" feed
"""

import math
import re
import asyncio
from collections import Counter
from services.tmdb import search_movies_tmdb, normalize_movie, TMDB_API_KEY, BASE_URL
from services.vibe_engine import score_movie, DIMENSIONS
import httpx

STOPWORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","was","are","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","need",
    "he","she","it","they","we","i","you","his","her","its","their","our","my",
    "this","that","these","those","who","which","what","when","where","how","why",
    "not","no","nor","so","yet","both","either","neither","each","few","more",
    "most","other","some","such","than","too","very","just","about","after",
    "before","between","into","through","during","while","although","though",
    "film","movie","story","life","new","one","two","man","woman","world","time",
    "find","must","take","make","comes","become","goes","tells","follows","set",
}


def tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def build_tfidf(documents: list[str]) -> list[dict]:
    """
    Builds TF-IDF vectors for a list of documents.
    Returns list of {term: tfidf_score} dicts.
    """
    N = len(documents)
    tokenized = [tokenize(doc) for doc in documents]

    # Document frequency: how many docs contain each term
    df = Counter()
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1

    # Build TF-IDF for each doc
    vectors = []
    for tokens in tokenized:
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec = {}
        for term, count in tf.items():
            tf_score = count / total
            idf_score = math.log((N + 1) / (df[term] + 1)) + 1  # smoothed IDF
            vec[term] = tf_score * idf_score
        vectors.append(vec)

    return vectors


def cosine_similarity(v1: dict, v2: dict) -> float:
    common = set(v1) & set(v2)
    if not common:
        return 0.0
    dot = sum(v1[t] * v2[t] for t in common)
    mag1 = math.sqrt(sum(x**2 for x in v1.values()))
    mag2 = math.sqrt(sum(x**2 for x in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


async def fetch_similar_from_tmdb(movie_id: int) -> list:
    """Fetch TMDB's own similar movies + recommendations as candidate pool."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r1, r2 = await asyncio.gather(
                client.get(f"{BASE_URL}/movie/{movie_id}/similar",
                           params={"api_key": TMDB_API_KEY, "page": 1}),
                client.get(f"{BASE_URL}/movie/{movie_id}/recommendations",
                           params={"api_key": TMDB_API_KEY, "page": 1}),
            )
            results = []
            for r in [r1, r2]:
                try:
                    results.extend(r.json().get("results", []))
                except:
                    pass
            return results
    except Exception as e:
        print(f"Similar fetch error: {e}")
        return []


async def get_movie_details_full(movie_id: int) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{BASE_URL}/movie/{movie_id}",
                params={"api_key": TMDB_API_KEY, "language": "en-US"}
            )
            return r.json()
    except:
        return {}


async def recommend_similar(movie_id: int, movie_title: str = "") -> dict:
    """
    Given a movie, find similar ones using:
    1. Fetch candidates from TMDB similar/recommendations
    2. Re-rank using TF-IDF cosine similarity on overviews
    Returns ranked list with similarity scores.
    """
    # Get source movie details
    source = await get_movie_details_full(movie_id)
    if not source:
        return {"results": [], "source_title": movie_title}

    source_overview = source.get("overview", "") or ""
    source_title = source.get("title", movie_title)

    # Fetch candidates
    candidates = await fetch_similar_from_tmdb(movie_id)

    # Deduplicate candidates
    seen = set()
    unique_candidates = []
    for m in candidates:
        if m.get("id") and m["id"] not in seen and m["id"] != movie_id:
            seen.add(m["id"])
            unique_candidates.append(m)

    if not unique_candidates:
        return {"results": [], "source_title": source_title}

    # Build TF-IDF corpus: source first, then candidates
    overviews = [source_overview] + [m.get("overview", "") or "" for m in unique_candidates]
    tfidf_vectors = build_tfidf(overviews)

    source_vec = tfidf_vectors[0]
    candidate_vecs = tfidf_vectors[1:]

    # Score each candidate
    scored = []
    for i, movie in enumerate(unique_candidates):
        sim = cosine_similarity(source_vec, candidate_vecs[i])
        # Combine text similarity with popularity for final score
        popularity_boost = min(movie.get("popularity", 0) / 1000, 0.2)
        final_score = sim + popularity_boost
        scored.append({
            **normalize_movie(movie),
            "similarity": round(sim * 100),
            "final_score": final_score,
        })

    scored.sort(key=lambda m: m["final_score"], reverse=True)

    return {
        "results": scored[:10],
        "source_title": source_title,
        "source_id": movie_id,
    }


# ── Taste Profile ────────────────────────────────────────────────────────────

GENRE_NAMES = {
    28:"Action", 12:"Adventure", 16:"Animation", 35:"Comedy", 80:"Crime",
    99:"Documentary", 18:"Drama", 10751:"Family", 14:"Fantasy", 36:"History",
    27:"Horror", 10402:"Music", 9648:"Mystery", 10749:"Romance", 878:"Sci-Fi",
    53:"Thriller", 10752:"War", 37:"Western",
}

def build_taste_profile(watched_movies: list) -> dict:
    """
    Analyzes a user's watched list to build their taste profile.
    Returns:
    - top genres (weighted by user rating if available)
    - average vibe dimension scores
    - personality label
    - stats
    """
    if not watched_movies:
        return {}

    genre_scores = Counter()
    dim_totals = {d: 0.0 for d in DIMENSIONS}
    total_rating = 0
    rated_count = 0

    for movie in watched_movies:
        weight = (movie.get("userRating") or 3) / 5.0  # normalize 1-5 → 0.2-1.0
        weight = max(weight, 0.2)

        # Genre scoring
        for gid in (movie.get("genre_ids") or []):
            genre_scores[gid] += weight

        # Vibe dimension scoring
        vibe = score_movie(movie)
        for d in DIMENSIONS:
            dim_totals[d] += vibe[d] * weight

        if movie.get("userRating"):
            total_rating += movie["userRating"]
            rated_count += 1

    n = len(watched_movies)
    avg_dims = {d: round(dim_totals[d] / n, 2) for d in DIMENSIONS}

    # Top genres
    top_genre_ids = [gid for gid, _ in genre_scores.most_common(5)]
    top_genres = [{"id": gid, "name": GENRE_NAMES.get(gid, "Unknown"), "score": round(genre_scores[gid], 1)}
                  for gid in top_genre_ids]

    # Personality label based on dominant dimensions
    dominant = max(avg_dims, key=avg_dims.get)
    personality_map = {
        "complexity": ("The Thinker", "You love films that challenge your mind"),
        "darkness":   ("The Dark Soul", "You're drawn to grim, intense stories"),
        "humor":      ("The Laugher", "Life's too short for serious movies"),
        "action":     ("The Thrill Seeker", "Non-stop action is your thing"),
        "emotion":    ("The Feeler", "You're here for the emotional gut-punches"),
        "suspense":   ("The Edge-Sitter", "You love being kept on the edge of your seat"),
    }
    label, tagline = personality_map.get(dominant, ("The Cinephile", "You appreciate great cinema"))

    avg_user_rating = round(total_rating / rated_count, 1) if rated_count else None

    return {
        "top_genres": top_genres,
        "vibe_profile": avg_dims,
        "personality_label": label,
        "personality_tagline": tagline,
        "dominant_dimension": dominant,
        "total_watched": n,
        "avg_user_rating": avg_user_rating,
        "rated_count": rated_count,
    }


async def get_for_you_feed(watched_movies: list) -> list:
    """
    Generates a personalized "For You" feed based on taste profile.
    Uses top genres to fetch movies, then ranks by vibe similarity.
    """
    if not watched_movies:
        return []

    profile = build_taste_profile(watched_movies)
    if not profile:
        return []

    watched_ids = {m.get("id") for m in watched_movies}
    top_genre_ids = [g["id"] for g in profile["top_genres"][:3]]
    target_vibe = profile["vibe_profile"]

    async def fetch_genre_movies(gid):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{BASE_URL}/discover/movie",
                    params={
                        "api_key": TMDB_API_KEY,
                        "with_genres": gid,
                        "sort_by": "popularity.desc",
                        "vote_count.gte": 200,
                        "page": 1,
                    }
                )
                return r.json().get("results", [])
        except:
            return []

    batches = await asyncio.gather(*[fetch_genre_movies(g) for g in top_genre_ids])

    # Merge + deduplicate + exclude already watched
    seen = set()
    candidates = []
    for batch in batches:
        for m in batch:
            mid = m.get("id")
            if mid and mid not in seen and mid not in watched_ids:
                seen.add(mid)
                candidates.append(m)

    # Rank by vibe similarity to user's taste profile
    from services.vibe_engine import cosine_sim
    scored = []
    for m in candidates:
        mvibe = score_movie(m)
        sim = cosine_sim(mvibe, target_vibe)
        scored.append({**normalize_movie(m), "match_pct": round(sim * 100)})

    scored.sort(key=lambda m: m["match_pct"], reverse=True)
    return scored[:12]