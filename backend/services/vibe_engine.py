"""
MovieAI Vibe Engine
--------------------
Natural language movie filtering using weighted attribute scoring.

Understands queries like:
  - "less complicated than Interstellar"
  - "darker than John Wick"
  - "something funnier than Deadpool"
  - "more emotional, less action"
  - "simple feel-good movie"
  - "mind-bending like Inception"

AI Technique: Multi-dimensional weighted attribute vectors + cosine similarity
"""

import re
import asyncio
from difflib import SequenceMatcher
from services.tmdb import search_movies_tmdb, normalize_movie, TMDB_API_KEY, BASE_URL
import httpx

# ─── Movie Attribute Dimensions ─────────────────────────────────────────────
# Each movie gets scored 0.0–1.0 on these axes.
# These are derived from genres, keywords, overview text analysis.

DIMENSIONS = ["complexity", "darkness", "humor", "action", "emotion", "suspense"]

# Genre → dimension weights
# (genre_id, genre_name): {dimension: weight}
GENRE_WEIGHTS = {
    28:  {"action": 0.9, "complexity": 0.3, "darkness": 0.4},          # Action
    12:  {"action": 0.6, "emotion": 0.5, "complexity": 0.3},           # Adventure
    16:  {"humor": 0.5, "emotion": 0.6, "complexity": 0.2},            # Animation
    35:  {"humor": 0.9, "darkness": 0.1, "complexity": 0.2},           # Comedy
    80:  {"darkness": 0.8, "suspense": 0.7, "complexity": 0.5},        # Crime
    99:  {"complexity": 0.5, "emotion": 0.4},                          # Documentary
    18:  {"emotion": 0.8, "complexity": 0.5, "darkness": 0.4},         # Drama
    10751: {"humor": 0.5, "emotion": 0.7, "complexity": 0.1},          # Family
    14:  {"complexity": 0.6, "action": 0.5, "emotion": 0.4},           # Fantasy
    36:  {"complexity": 0.7, "emotion": 0.5},                          # History
    27:  {"darkness": 0.9, "suspense": 0.8, "complexity": 0.4},        # Horror
    10402: {"emotion": 0.7, "complexity": 0.3},                        # Music
    9648: {"suspense": 0.9, "complexity": 0.8, "darkness": 0.5},       # Mystery
    10749: {"emotion": 0.9, "humor": 0.3, "complexity": 0.2},          # Romance
    878:  {"complexity": 0.9, "action": 0.5, "suspense": 0.6},         # Sci-Fi
    53:   {"suspense": 0.9, "darkness": 0.6, "complexity": 0.5},       # Thriller
    10752: {"action": 0.8, "darkness": 0.7, "emotion": 0.6},           # War
    37:   {"action": 0.5, "complexity": 0.3, "emotion": 0.4},          # Western
}

# Overview keyword → dimension signal
KEYWORD_SIGNALS = {
    "complexity":  ["complex", "twist", "nonlinear", "timeline", "mind-bending", "philosophical",
                    "layers", "ambiguous", "surreal", "dream", "illusion", "paradox", "theory",
                    "quantum", "dimension", "multiverse", "memory", "identity", "reality"],
    "darkness":    ["dark", "grim", "brutal", "violent", "death", "murder", "war", "tragedy",
                    "evil", "corrupt", "horror", "terror", "apocalypse", "dystopia", "bleak",
                    "nihilism", "grief", "trauma", "abuse", "revenge"],
    "humor":       ["comedy", "funny", "hilarious", "laugh", "joke", "witty", "sarcastic",
                    "parody", "satire", "absurd", "quirky", "lighthearted", "comic"],
    "action":      ["action", "fight", "battle", "chase", "explosion", "gun", "war", "combat",
                    "hero", "villain", "mission", "assassin", "agent", "heist", "rescue"],
    "emotion":     ["love", "loss", "family", "friendship", "sacrifice", "hope", "inspire",
                    "heart", "touching", "moving", "beautiful", "bond", "relationship", "tears"],
    "suspense":    ["suspense", "thriller", "mystery", "secret", "unknown", "tension", "paranoia",
                    "conspiracy", "spy", "hidden", "reveal", "plot", "investigation", "clue"],
}

# Natural language direction parsing
COMPARISON_PATTERNS = [
    # "less X than Y" / "more X than Y"
    (r"(less|more|not as|way more|way less|much more|much less|a bit more|a bit less)\s+"
     r"(\w+)\s+(?:than|like|as)\s+(.+)", "comparative"),
    # "simpler than X" / "darker than X"
    (r"(simpler|darker|funnier|scarier|lighter|heavier|deeper|shallower|"
     r"happier|sadder|slower|faster|calmer|crazier)\s+(?:than|like|as)\s+(.+)", "adjective"),
    # "like X but less dark"
    (r"like\s+(.+?)\s+but\s+(less|more)\s+(\w+)", "like_but"),
    # pure mood: "something dark and complex"
    (r"something\s+(.+)", "mood_only"),
    # "feel-good", "mind-bending", standalone
    (r"(feel.good|mind.bend|lighthearted|uplifting|feel good|mind bending)", "mood_tag"),
]

ADJECTIVE_MAP = {
    "simpler":    ("complexity", -1),
    "darker":     ("darkness",   +1),
    "funnier":    ("humor",      +1),
    "scarier":    ("suspense",   +1),
    "lighter":    ("darkness",   -1),
    "heavier":    ("emotion",    +1),
    "deeper":     ("complexity", +1),
    "shallower":  ("complexity", -1),
    "happier":    ("humor",      +1),
    "sadder":     ("emotion",    +1),
    "calmer":     ("action",     -1),
    "crazier":    ("complexity", +1),
}

MOOD_TAG_MAP = {
    "feel-good":    {"humor": +0.4, "emotion": +0.3, "darkness": -0.5},
    "feel good":    {"humor": +0.4, "emotion": +0.3, "darkness": -0.5},
    "mind-bending": {"complexity": +0.5, "suspense": +0.3},
    "mind bending": {"complexity": +0.5, "suspense": +0.3},
    "lighthearted": {"humor": +0.4, "darkness": -0.5, "action": -0.2},
    "uplifting":    {"emotion": +0.4, "darkness": -0.4, "humor": +0.2},
}

WORD_TO_DIMENSION = {
    "complex": "complexity", "complicated": "complexity", "deep": "complexity",
    "simple": "complexity", "easy": "complexity", "straightforward": "complexity",
    "dark": "darkness", "grim": "darkness", "light": "darkness", "bright": "darkness",
    "funny": "humor", "humorous": "humor", "serious": "humor", "comedy": "humor",
    "action": "action", "intense": "action", "slow": "action", "calm": "action",
    "emotional": "emotion", "touching": "emotion", "cold": "emotion",
    "suspenseful": "suspense", "tense": "suspense", "thrilling": "suspense",
}

# ─── Score a single movie on all dimensions ──────────────────────────────────
def score_movie(movie: dict) -> dict:
    scores = {d: 0.0 for d in DIMENSIONS}
    counts = {d: 0 for d in DIMENSIONS}

    # Genre-based scoring
    for gid in movie.get("genre_ids", []):
        if gid in GENRE_WEIGHTS:
            for dim, w in GENRE_WEIGHTS[gid].items():
                scores[dim] += w
                counts[dim] += 1

    # Overview keyword scoring
    overview = (movie.get("overview") or "").lower()
    for dim, keywords in KEYWORD_SIGNALS.items():
        hits = sum(1 for kw in keywords if kw in overview)
        if hits:
            scores[dim] += min(hits * 0.15, 0.6)
            counts[dim] += 1

    # Normalize: average contributions, clamp 0–1
    final = {}
    for dim in DIMENSIONS:
        if counts[dim] > 0:
            final[dim] = min(scores[dim] / max(counts[dim], 1), 1.0)
        else:
            final[dim] = 0.3  # neutral default
    return final


# ─── Parse natural language query ────────────────────────────────────────────
def parse_vibe_query(query: str) -> dict:
    """
    Returns:
    {
      "reference_movie": "Interstellar" or None,
      "deltas": {"complexity": -0.3, "darkness": +0.2, ...},
      "mode": "comparative" | "mood_only" | "reference_match",
      "raw": original query
    }
    """
    q = query.strip().lower()
    deltas = {}
    reference_movie = None
    mode = "mood_only"

    # Pattern: "less/more X than MOVIE"
    m = re.search(
        r"(less|more|not as|way more|way less|much more|much less|a bit more|a bit less)\s+"
        r"(complex|complicated|dark|funny|scary|intense|emotional|suspenseful|simple|action)\w*"
        r"\s+(?:than|like|as)\s+(.+)", q
    )
    if m:
        direction = -1 if m.group(1) in ("less", "not as", "way less", "much less", "a bit less") else +1
        word = m.group(2)
        reference_movie = m.group(3).strip().title()
        dim = WORD_TO_DIMENSION.get(word, "complexity")
        deltas[dim] = direction * 0.4
        mode = "comparative"
        return {"reference_movie": reference_movie, "deltas": deltas, "mode": mode, "raw": query}

    # Pattern: adjective comparative "simpler than MOVIE"
    m = re.search(
        r"(simpler|darker|funnier|scarier|lighter|heavier|deeper|happier|sadder|calmer|crazier)"
        r"\s+(?:than|like|as)\s+(.+)", q
    )
    if m:
        adj = m.group(1)
        reference_movie = m.group(2).strip().title()
        if adj in ADJECTIVE_MAP:
            dim, direction = ADJECTIVE_MAP[adj]
            deltas[dim] = direction * 0.4
        mode = "comparative"
        return {"reference_movie": reference_movie, "deltas": deltas, "mode": mode, "raw": query}

    # Pattern: "like MOVIE but less/more X"
    m = re.search(r"like\s+(.+?)\s+but\s+(less|more)\s+(\w+)", q)
    if m:
        reference_movie = m.group(1).strip().title()
        direction = -1 if m.group(2) == "less" else +1
        word = m.group(3)
        dim = WORD_TO_DIMENSION.get(word, "complexity")
        deltas[dim] = direction * 0.4
        mode = "comparative"
        return {"reference_movie": reference_movie, "deltas": deltas, "mode": mode, "raw": query}

    # Mood tags: "feel-good", "mind-bending"
    for tag, tag_deltas in MOOD_TAG_MAP.items():
        if tag in q:
            deltas.update(tag_deltas)
            mode = "mood_only"

    # Loose word scanning for mood-only queries
    for word, dim in WORD_TO_DIMENSION.items():
        if word in q:
            # "not X" or "less X" → negative
            neg = bool(re.search(rf"(not|less|no|avoid)\s+\w*{word}", q))
            deltas[dim] = deltas.get(dim, 0) + (-0.3 if neg else +0.3)

    # "something like MOVIE"
    m = re.search(r"(?:like|similar to|same as)\s+(.+)", q)
    if m and not reference_movie:
        reference_movie = m.group(1).strip().title()
        mode = "reference_match"

    return {"reference_movie": reference_movie, "deltas": deltas, "mode": mode, "raw": query}


# ─── Fetch + score reference movie ───────────────────────────────────────────
async def get_reference_scores(movie_title: str) -> dict | None:
    results = await search_movies_tmdb(movie_title)
    if not results:
        return None
    # Pick best match
    best = max(results, key=lambda m: m.get("popularity", 0))
    return score_movie(best)


# ─── Fetch candidate movies ───────────────────────────────────────────────────
async def fetch_candidates(deltas: dict, reference_scores: dict | None) -> list:
    """
    Determines what genres to search based on target dimension profile,
    then fetches candidates from TMDB.
    """
    # Build target profile
    if reference_scores:
        target = {d: reference_scores[d] + deltas.get(d, 0) for d in DIMENSIONS}
    else:
        # Pure mood — start from neutral
        target = {d: 0.5 + deltas.get(d, 0) for d in DIMENSIONS}

    # Clamp 0–1
    target = {d: max(0.0, min(1.0, v)) for d, v in target.items()}

    # Pick best matching genres based on target
    genre_scores = {}
    for gid, gweights in GENRE_WEIGHTS.items():
        score = 0
        for dim, w in gweights.items():
            t = target.get(dim, 0.5)
            score += 1.0 - abs(t - w)
        genre_scores[gid] = score

    top_genres = sorted(genre_scores, key=genre_scores.get, reverse=True)[:3]

    # Fetch movies for each top genre in parallel
    async def fetch_genre(gid):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{BASE_URL}/discover/movie",
                    params={
                        "api_key": TMDB_API_KEY,
                        "with_genres": gid,
                        "sort_by": "popularity.desc",
                        "vote_count.gte": 100,
                        "page": 1,
                    }
                )
                r.raise_for_status()
                return r.json().get("results", [])
        except:
            return []

    results = await asyncio.gather(*[fetch_genre(g) for g in top_genres])
    all_movies = []
    seen = set()
    for batch in results:
        for m in batch:
            if m.get("id") not in seen:
                seen.add(m["id"])
                all_movies.append(m)

    return all_movies, target


# ─── Cosine similarity between two dimension vectors ──────────────────────────
def cosine_sim(a: dict, b: dict) -> float:
    dims = DIMENSIONS
    dot = sum(a.get(d, 0) * b.get(d, 0) for d in dims)
    mag_a = sum(a.get(d, 0) ** 2 for d in dims) ** 0.5
    mag_b = sum(b.get(d, 0) ** 2 for d in dims) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ─── MAIN VIBE SEARCH ────────────────────────────────────────────────────────
async def vibe_search(query: str) -> dict:
    """
    Full pipeline:
    1. Parse natural language
    2. Get reference movie scores (if any)
    3. Compute target dimension profile
    4. Fetch candidates from TMDB
    5. Score each candidate via cosine similarity
    6. Return ranked results with match % and dimension breakdown
    """
    parsed = parse_vibe_query(query)
    reference_scores = None

    if parsed["reference_movie"]:
        reference_scores = await get_reference_scores(parsed["reference_movie"])

    candidates, target = await fetch_candidates(parsed["deltas"], reference_scores)

    if not candidates:
        return {"results": [], "target_profile": target, "parsed": parsed}

    # Score each candidate
    scored = []
    for movie in candidates:
        movie_scores = score_movie(movie)
        sim = cosine_sim(movie_scores, target)
        match_pct = round(sim * 100)
        scored.append({
            **normalize_movie(movie),
            "match_pct": match_pct,
            "vibe_scores": movie_scores,
        })

    # Sort by match %
    scored = sorted(scored, key=lambda m: m["match_pct"], reverse=True)

    # Deduplicate
    seen = set()
    unique = []
    for m in scored:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique.append(m)

    return {
        "results": unique[:12],
        "target_profile": target,
        "reference_movie": parsed["reference_movie"],
        "parsed_intent": parsed["mode"],
        "deltas_applied": parsed["deltas"],
    }