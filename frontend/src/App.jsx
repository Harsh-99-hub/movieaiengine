import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import "./App.css";
import StatsTab from "./StatsTab";

const API_BASE = "https://movieaiengine-production.up.railway.app/api";
const VIBE_EXAMPLES = [
  "less complicated than Interstellar","darker than John Wick",
  "like Inception but funnier","simpler than Tenet",
  "something feel-good","more emotional than Avengers",
];

const getWatched = () => JSON.parse(localStorage.getItem("mav_watched") || "[]");
const saveWatched = (list) => localStorage.setItem("mav_watched", JSON.stringify(list));

// ── Reusable components ──────────────────────────────────────────────────────

function StarRating({ rating }) {
  const stars = Math.round(rating / 2);
  return (
    <div className="stars">
      {[1,2,3,4,5].map(s=>(
        <span key={s} className={s<=stars?"star filled":"star"}>★</span>
      ))}
      <span className="rating-num">{rating}/10</span>
    </div>
  );
}

function MatchBar({ pct, label }) {
  const color = pct>=75?"#4ade80":pct>=50?"#f4a261":"#888";
  return (
    <div className="match-wrap">
      <div className="match-bar-bg">
        <div className="match-bar-fill" style={{width:`${pct}%`,background:color}}/>
      </div>
      <span className="match-label" style={{color}}>{pct}% {label||"match"}</span>
    </div>
  );
}

function VibeProfile({ profile, reference }) {
  if (!profile) return null;
  const dims=[
    {key:"complexity",label:"Complexity",emoji:"🧠"},
    {key:"darkness",label:"Darkness",emoji:"🖤"},
    {key:"humor",label:"Humor",emoji:"😂"},
    {key:"action",label:"Action",emoji:"💥"},
    {key:"emotion",label:"Emotion",emoji:"💔"},
    {key:"suspense",label:"Suspense",emoji:"😰"},
  ];
  return (
    <div className="vibe-profile">
      <p className="vibe-profile-title">
        🎯 Target Vibe {reference&&<span>· based on <strong>{reference}</strong></span>}
      </p>
      <div className="vibe-bars">
        {dims.map(d=>{
          const val=Math.round((profile[d.key]||0)*100);
          return (
            <div key={d.key} className="vibe-row">
              <span className="vibe-dim-label">{d.emoji} {d.label}</span>
              <div className="vibe-bar-bg"><div className="vibe-bar-fill" style={{width:`${val}%`}}/></div>
              <span className="vibe-pct">{val}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Movie Card ───────────────────────────────────────────────────────────────

function MovieCard({ movie, showVibe, showSimilarity, isWatched, onToggleWatched, onMoreLikeThis }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div className={`movie-card ${hovered?"hovered":""} ${isWatched?"watched-card":""}`}
      onMouseEnter={()=>setHovered(true)} onMouseLeave={()=>setHovered(false)}>
      <div className="poster-wrap">
        {movie.poster
          ? <img src={movie.poster} alt={movie.title} className="poster"/>
          : <div className="no-poster">🎬</div>}
        <div className="overlay">
          <p className="overview">{movie.overview?.slice(0,140)}...</p>
          {onMoreLikeThis && (
            <button className="more-like-btn" onClick={e=>{e.stopPropagation();onMoreLikeThis(movie);}}>
              🔍 More like this
            </button>
          )}
        </div>
        <button className={`watch-tick ${isWatched?"ticked":""}`}
          onClick={e=>{e.stopPropagation();onToggleWatched(movie);}}
          title={isWatched?"Remove from watched":"Mark as watched"}>
          {isWatched?"✓":"+"}
        </button>
        {isWatched&&<div className="watched-ribbon">Watched</div>}
      </div>
      <div className="card-info">
        <h3 className="movie-title">{movie.title}</h3>
        <div className="meta">
          <span className="year">{movie.release_year||"—"}</span>
          <StarRating rating={movie.rating}/>
        </div>
        {showVibe&&movie.match_pct!==undefined&&<MatchBar pct={movie.match_pct}/>}
        {showSimilarity&&movie.similarity!==undefined&&<MatchBar pct={movie.similarity} label="similar"/>}
      </div>
    </div>
  );
}

// ── Watched Card ─────────────────────────────────────────────────────────────

function WatchedCard({ movie, onRemove, onRate, onMoreLikeThis }) {
  const [userRating,setUserRating]=useState(movie.userRating||0);
  const [hovered,setHovered]=useState(false);
  const [hoverStar,setHoverStar]=useState(0);
  const handleRate=(r)=>{setUserRating(r);onRate(movie.id,r);};
  return (
    <div className={`movie-card watched-card ${hovered?"hovered":""}`}
      onMouseEnter={()=>setHovered(true)} onMouseLeave={()=>setHovered(false)}>
      <div className="poster-wrap">
        {movie.poster?<img src={movie.poster} alt={movie.title} className="poster"/>:<div className="no-poster">🎬</div>}
        <div className="overlay">
          <p className="overview">{movie.overview?.slice(0,120)}...</p>
          <button className="more-like-btn" onClick={e=>{e.stopPropagation();onMoreLikeThis(movie);}}>
            🔍 More like this
          </button>
        </div>
        <div className="watched-ribbon">Watched ✓</div>
        <button className="watch-tick ticked" onClick={()=>onRemove(movie.id)} title="Remove">✕</button>
      </div>
      <div className="card-info">
        <h3 className="movie-title">{movie.title}</h3>
        <div className="meta">
          <span className="year">{movie.release_year||"—"}</span>
          <span className="tmdb-score">TMDB {movie.rating}/10</span>
        </div>
        <div className="user-rating-wrap">
          <span className="user-rating-label">Your rating:</span>
          <div className="user-stars">
            {[1,2,3,4,5].map(s=>(
              <span key={s} className={`user-star ${s<=(hoverStar||userRating)?"active":""}`}
                onMouseEnter={()=>setHoverStar(s)} onMouseLeave={()=>setHoverStar(0)}
                onClick={()=>handleRate(s)}>★</span>
            ))}
          </div>
          {userRating>0&&<span className="user-rating-val">{userRating}/5</span>}
        </div>
        {movie.watchedAt&&(
          <p className="watched-date">
            {new Date(movie.watchedAt).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Taste Profile Panel ──────────────────────────────────────────────────────

function TasteProfilePanel({ profile }) {
  if (!profile||!profile.personality_label) return null;
  const dims=[
    {key:"complexity",emoji:"🧠"},{key:"darkness",emoji:"🖤"},
    {key:"humor",emoji:"😂"},{key:"action",emoji:"💥"},
    {key:"emotion",emoji:"💔"},{key:"suspense",emoji:"😰"},
  ];
  return (
    <div className="taste-panel">
      <div className="taste-header">
        <div>
          <h3 className="taste-label">{profile.personality_label}</h3>
          <p className="taste-tagline">{profile.personality_tagline}</p>
        </div>
        <div className="taste-stats">
          <div className="taste-stat"><span className="ts-num">{profile.total_watched}</span><span className="ts-label">watched</span></div>
          {profile.avg_user_rating&&<div className="taste-stat"><span className="ts-num">{profile.avg_user_rating}/5</span><span className="ts-label">avg rating</span></div>}
          <div className="taste-stat"><span className="ts-num">{profile.rated_count}</span><span className="ts-label">rated</span></div>
        </div>
      </div>

      <div className="taste-body">
        <div className="taste-section">
          <p className="taste-section-title">Top Genres</p>
          <div className="genre-pills">
            {(profile.top_genres||[]).map(g=>(
              <span key={g.id} className="genre-pill">{g.name}</span>
            ))}
          </div>
        </div>
        <div className="taste-section">
          <p className="taste-section-title">Your Vibe DNA</p>
          <div className="vibe-bars compact">
            {dims.map(d=>{
              const val=Math.round(((profile.vibe_profile||{})[d.key]||0)*100);
              return (
                <div key={d.key} className="vibe-row compact-row">
                  <span className="vibe-dim-label compact-label">{d.emoji}</span>
                  <div className="vibe-bar-bg"><div className="vibe-bar-fill taste-fill" style={{width:`${val}%`}}/></div>
                  <span className="vibe-pct">{val}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Similar Movies Modal ──────────────────────────────────────────────────────

function SimilarModal({ movie, isWatched, onToggleWatched, onClose }) {
  const [results,setResults]=useState([]);
  const [loading,setLoading]=useState(true);
  const [sourceTitle,setSourceTitle]=useState("");

  useEffect(()=>{
    if (!movie) return;
    setLoading(true);
    axios.get(`${API_BASE}/recommend/similar`,{params:{movie_id:movie.id,title:movie.title}})
      .then(res=>{setResults(res.data.results||[]);setSourceTitle(res.data.source_title||movie.title);})
      .catch(()=>setResults([]))
      .finally(()=>setLoading(false));
  },[movie]);

  if (!movie) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2 className="modal-title">Movies similar to</h2>
            <p className="modal-subtitle">"{sourceTitle}"</p>
            <p className="modal-ai-tag">🤖 AI: TF-IDF cosine similarity on overviews</p>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        {loading?(
          <div className="modal-loading">
            {[...Array(4)].map((_,i)=><div key={i} className="skeleton-card modal-skeleton"/>)}
          </div>
        ):(
          <div className="modal-grid">
            {results.map(m=>(
              <MovieCard key={m.id} movie={m} showSimilarity={true}
                isWatched={isWatched(m.id)} onToggleWatched={onToggleWatched}
                onMoreLikeThis={null}/>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Query Interpret ──────────────────────────────────────────────────────────

function QueryInterpret({ original, interpreted, strategy, count }) {
  if (!interpreted) return null;
  const changed=interpreted.toLowerCase()!==original.toLowerCase().trim();
  const tag={fuzzy_split:"🔀 fuzzy",person_search:"🎬 person",with_year:"📅 year",keyword_fallback:"🔑 keyword"}[strategy];
  return (
    <div className="interpret-bar">
      {changed&&<span>🧠 Searching: <strong>"{interpreted}"</strong></span>}
      {tag&&<span className="strategy-tag">{tag}</span>}
      {count>0&&<span className="result-count">{count} results</span>}
    </div>
  );
}

// ── Watched Stats ────────────────────────────────────────────────────────────

function WatchStats({ list }) {
  if (!list.length) return null;
  const rated=list.filter(m=>m.userRating>0);
  const avg=rated.length?(rated.reduce((s,m)=>s+m.userRating,0)/rated.length).toFixed(1):null;
  const avgT=(list.reduce((s,m)=>s+(m.rating||0),0)/list.length).toFixed(1);
  return (
    <div className="watch-stats">
      <div className="stat-pill">🎬 <strong>{list.length}</strong> watched</div>
      {avg&&<div className="stat-pill">⭐ avg <strong>{avg}/5</strong> yours</div>}
      <div className="stat-pill">📊 avg TMDB <strong>{avgT}/10</strong></div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
export default function App() {
  const [tab,setTab]=useState("search");
  const [query,setQuery]=useState("");
  const [movies,setMovies]=useState([]);
  const [trending,setTrending]=useState([]);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [searched,setSearched]=useState(false);
  const [searchMeta,setSearchMeta]=useState(null);

  const [vibeQuery,setVibeQuery]=useState("");
  const [vibeResults,setVibeResults]=useState([]);
  const [vibeProfile,setVibeProfile]=useState(null);
  const [vibeRef,setVibeRef]=useState(null);
  const [vibeLoading,setVibeLoading]=useState(false);
  const [vibeError,setVibeError]=useState("");
  const [vibeSearched,setVibeSearched]=useState(false);

  const [watched,setWatched]=useState(getWatched());
  const [watchFilter,setWatchFilter]=useState("all");
  const [tasteProfile,setTasteProfile]=useState(null);
  const [tasteLoading,setTasteLoading]=useState(false);

  const [forYou,setForYou]=useState([]);
  const [forYouLoading,setForYouLoading]=useState(false);

  const [similarMovie,setSimilarMovie]=useState(null);

  const inputRef=useRef();

  useEffect(()=>{
    axios.get(`${API_BASE}/movies/trending`).then(r=>setTrending(r.data.results||[])).catch(()=>{});
  },[]);

  // Load taste + for-you when watched tab opens
  useEffect(()=>{
    if (tab==="watched" && watched.length>0) {
      // Taste profile
      setTasteLoading(true);
      axios.post(`${API_BASE}/recommend/taste`,{watched})
        .then(r=>setTasteProfile(r.data)).catch(()=>{}).finally(()=>setTasteLoading(false));
      // For You
      setForYouLoading(true);
      axios.post(`${API_BASE}/recommend/foryou`,{watched})
        .then(r=>setForYou(r.data.results||[])).catch(()=>{}).finally(()=>setForYouLoading(false));
    }
  },[tab]);

  const isWatched=useCallback((id)=>watched.some(m=>m.id===id),[watched]);

  const toggleWatched=useCallback((movie)=>{
    let updated;
    if (isWatched(movie.id)) {
      updated=watched.filter(m=>m.id!==movie.id);
    } else {
      updated=[{...movie,watchedAt:new Date().toISOString(),userRating:0},...watched];
    }
    setWatched(updated);saveWatched(updated);
  },[watched,isWatched]);

  const removeWatched=(id)=>{const u=watched.filter(m=>m.id!==id);setWatched(u);saveWatched(u);};
  const rateMovie=(id,r)=>{const u=watched.map(m=>m.id===id?{...m,userRating:r}:m);setWatched(u);saveWatched(u);};

  const searchMovies=async()=>{
    const cq=query.trim().replace(/\s+/g," ");
    if (!cq) return;
    setLoading(true);setError("");setSearched(true);setSearchMeta(null);
    try {
      const res=await axios.get(`${API_BASE}/search`,{params:{q:cq}});
      setMovies(res.data.results||[]);
      setSearchMeta({original:cq,interpreted:res.data.query_interpreted,strategy:res.data.strategy,count:res.data.count});
      if (!res.data.results?.length) setError(`No results for "${cq}"`);
    } catch {setError("Backend not reachable. Is uvicorn running?");setMovies([]);}
    finally{setLoading(false);}
  };

  const searchVibe=async(q)=>{
    const vq=(q||vibeQuery).trim();
    if (!vq) return;
    setVibeLoading(true);setVibeError("");setVibeSearched(true);
    setVibeResults([]);setVibeProfile(null);setVibeRef(null);
    try {
      const res=await axios.get(`${API_BASE}/vibe`,{params:{q:vq}});
      setVibeResults(res.data.results||[]);
      setVibeProfile(res.data.target_profile);setVibeRef(res.data.reference_movie);
      if (!res.data.results?.length) setVibeError("No matches — try rephrasing");
    } catch {setVibeError("Backend not reachable.");}
    finally{setVibeLoading(false);}
  };

  const clearSearch=()=>{setQuery("");setMovies([]);setSearched(false);setError("");setSearchMeta(null);inputRef.current?.focus();};
  const displayMovies=searched?movies:trending;
  const filteredWatched=watched.filter(m=>watchFilter==="rated"?m.userRating>0:watchFilter==="unrated"?!m.userRating:true);

  return (
    <div className="app">
      {/* Similar Modal */}
      {similarMovie&&(
        <SimilarModal movie={similarMovie} isWatched={isWatched}
          onToggleWatched={toggleWatched} onClose={()=>setSimilarMovie(null)}/>
      )}

      <header className="header">
        <div className="logo" onClick={()=>{setTab("search");clearSearch();}}>
          <span className="logo-icon">🎬</span>
          <span className="logo-text">Movie<span className="accent">AI</span></span>
        </div>
        <p className="tagline">Discover your next favorite film</p>

        <div className="tabs">
          <button className={`tab-btn ${tab==="search"?"active":""}`} onClick={()=>setTab("search")}>🔍 Search</button>
          <button className={`tab-btn ${tab==="vibe"?"active":""}`} onClick={()=>setTab("vibe")}>🧠 Vibe AI</button>
          <button className={`tab-btn ${tab==="watched"?"active":""}`} onClick={()=>setTab("watched")}>
            ✓ Watched {watched.length>0&&<span className="tab-badge">{watched.length}</span>}
          </button>
          <button className={`tab-btn ${tab==="stats"?"active":""}`} onClick={()=>setTab("stats")}>📊 Stats</button>
        </div>

        {tab==="search"&&(
          <div className="search-bar">
            <input ref={inputRef} type="text" placeholder='Try "johnwick", "tdk", "lotr"...'
              value={query} onChange={e=>setQuery(e.target.value)}
              onKeyDown={e=>e.key==="Enter"&&searchMovies()} className="search-input"/>
            <button onClick={searchMovies} className="search-btn" disabled={loading}>
              {loading?<span className="spinner"/>:"Search"}
            </button>
            {searched&&<button onClick={clearSearch} className="clear-btn">✕</button>}
          </div>
        )}

        {tab==="vibe"&&(
          <div className="vibe-input-wrap">
            <div className="search-bar">
              <input type="text" placeholder='"less complicated than Interstellar"'
                value={vibeQuery} onChange={e=>setVibeQuery(e.target.value)}
                onKeyDown={e=>e.key==="Enter"&&searchVibe()} className="search-input vibe-input"/>
              <button onClick={()=>searchVibe()} className="search-btn vibe-btn" disabled={vibeLoading}>
                {vibeLoading?<span className="spinner"/>:"Find Vibes"}
              </button>
            </div>
            <div className="vibe-chips">
              {VIBE_EXAMPLES.map((ex,i)=>(
                <button key={i} className="vibe-chip" onClick={()=>{setVibeQuery(ex);searchVibe(ex);}}>{ex}</button>
              ))}
            </div>
          </div>
        )}
      </header>

      <main className="main">
        {/* ── Search Tab ── */}
        {tab==="search"&&(
          <>
            {error&&<div className="error-banner">⚠️ {error}</div>}
            {searched&&searchMeta&&<QueryInterpret {...searchMeta}/>}
            <h2 className="section-title">{searched?`Results for "${query}"`:"🔥 Trending This Week"}</h2>
            {loading?(
              <div className="loading-grid">{[...Array(8)].map((_,i)=><div key={i} className="skeleton-card" style={{animationDelay:`${i*0.08}s`}}/>)}</div>
            ):(
              <div className="movies-grid">
                {displayMovies.map(m=>(
                  <MovieCard key={m.id} movie={m} showVibe={false}
                    isWatched={isWatched(m.id)} onToggleWatched={toggleWatched}
                    onMoreLikeThis={setSimilarMovie}/>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── Vibe Tab ── */}
        {tab==="vibe"&&(
          <>
            {vibeError&&<div className="error-banner">⚠️ {vibeError}</div>}
            {!vibeSearched&&(
              <div className="vibe-intro">
                <h2 className="section-title">🧠 AI Vibe Search</h2>
                <p className="vibe-desc">Natural language movie discovery using <strong>cosine similarity</strong> across 6 AI-scored dimensions.</p>
                <div className="dim-legend">
                  {["🧠 Complexity","🖤 Darkness","😂 Humor","💥 Action","💔 Emotion","😰 Suspense"].map(d=>(
                    <span key={d} className="dim-badge-lg">{d}</span>
                  ))}
                </div>
              </div>
            )}
            {vibeSearched&&vibeProfile&&<VibeProfile profile={vibeProfile} reference={vibeRef}/>}
            {vibeLoading?(
              <div className="loading-grid">{[...Array(8)].map((_,i)=><div key={i} className="skeleton-card" style={{animationDelay:`${i*0.08}s`}}/>)}</div>
            ):(
              <div className="movies-grid">
                {vibeResults.map(m=>(
                  <MovieCard key={m.id} movie={m} showVibe={true}
                    isWatched={isWatched(m.id)} onToggleWatched={toggleWatched}
                    onMoreLikeThis={setSimilarMovie}/>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── Watched Tab ── */}
        {tab==="watched"&&(
          <>
            {watched.length===0?(
              <div className="empty-watched">
                <p className="empty-icon">🎬</p>
                <h3>No movies watched yet</h3>
                <p>Hit <strong>+</strong> on any movie card to mark it as watched</p>
                <button className="search-btn" style={{marginTop:16}} onClick={()=>setTab("search")}>Browse Movies</button>
              </div>
            ):(
              <>
                {/* Taste Profile */}
                {tasteLoading?(
                  <div className="taste-panel loading-taste"><span className="spinner"/> Building your taste profile...</div>
                ):(
                  <TasteProfilePanel profile={tasteProfile}/>
                )}

                {/* For You Feed */}
                {watched.length>=2&&(
                  <div className="for-you-section">
                    <h2 className="section-title">✨ Recommended For You
                      <span className="ai-method-tag">TF-IDF + Genre Profiling</span>
                    </h2>
                    {forYouLoading?(
                      <div className="loading-grid">{[...Array(4)].map((_,i)=><div key={i} className="skeleton-card"/>)}</div>
                    ):(
                      <div className="movies-grid">
                        {forYou.map(m=>(
                          <MovieCard key={m.id} movie={m} showVibe={true}
                            isWatched={isWatched(m.id)} onToggleWatched={toggleWatched}
                            onMoreLikeThis={setSimilarMovie}/>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Watched List */}
                <div className="watched-header">
                  <h2 className="section-title">✓ My Watched List</h2>
                  <div className="watch-filter-bar">
                    {["all","rated","unrated"].map(f=>(
                      <button key={f} className={`filter-btn ${watchFilter===f?"active":""}`} onClick={()=>setWatchFilter(f)}>
                        {f.charAt(0).toUpperCase()+f.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
                <WatchStats list={watched}/>
                <div className="movies-grid">
                  {filteredWatched.map(m=>(
                    <WatchedCard key={m.id} movie={m} onRemove={removeWatched}
                      onRate={rateMovie} onMoreLikeThis={setSimilarMovie}/>
                  ))}
                </div>
              </>
            )}
          </>
        )}
        {/* ── Stats Tab ── */}
        {tab==="stats"&&<StatsTab watched={watched}/>}
      </main>

      <footer className="footer">
        <p>Powered by <a href="https://www.themoviedb.org" target="_blank">TMDB</a> · AI: TF-IDF · Cosine Similarity · NLP · Genre Profiling · <span className="made-by">made by harshith</span></p>
      </footer>
    </div>
  );
}
