import { useEffect, useRef } from "react";

const GENRE_NAMES = {
  28:"Action",12:"Adventure",16:"Animation",35:"Comedy",80:"Crime",
  99:"Documentary",18:"Drama",10751:"Family",14:"Fantasy",36:"History",
  27:"Horror",10402:"Music",9648:"Mystery",10749:"Romance",878:"Sci-Fi",
  53:"Thriller",10752:"War",37:"Western",
};

const ACCENT  = "#e63946";
const PURPLE  = "#a78bfa";
const AMBER   = "#f4a261";
const GREEN   = "#4ade80";
const CYAN    = "#22d3ee";
const COLORS  = [ACCENT, PURPLE, AMBER, GREEN, CYAN, "#fb7185", "#34d399", "#60a5fa"];

function useCanvas(draw, deps) {
  const ref = useRef();
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = canvas.offsetWidth  * dpr;
    canvas.height = canvas.offsetHeight * dpr;
    ctx.scale(dpr, dpr);
    draw(ctx, canvas.offsetWidth, canvas.offsetHeight);
  }, deps);
  return ref;
}

// ── Donut Chart ──────────────────────────────────────────────────────────────
function DonutChart({ data, title }) {
  const ref = useCanvas((ctx, w, h) => {
    if (!data.length) return;
    const cx = w / 2, cy = h / 2;
    const r = Math.min(cx, cy) - 32;
    const inner = r * 0.58;
    const total = data.reduce((s, d) => s + d.value, 0);
    let angle = -Math.PI / 2;
    data.forEach((d, i) => {
      const slice = (d.value / total) * 2 * Math.PI;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, angle, angle + slice);
      ctx.closePath();
      ctx.fillStyle = COLORS[i % COLORS.length];
      ctx.fill();
      angle += slice;
    });
    // inner hole
    ctx.beginPath();
    ctx.arc(cx, cy, inner, 0, 2 * Math.PI);
    ctx.fillStyle = "#12121e";
    ctx.fill();
    // center text
    ctx.fillStyle = "#f0f0f5";
    ctx.font = "bold 22px 'DM Sans', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(total, cx, cy - 8);
    ctx.font = "12px 'DM Sans', sans-serif";
    ctx.fillStyle = "#8888aa";
    ctx.fillText("movies", cx, cy + 12);
  }, [data]);

  return (
    <div className="chart-card">
      <p className="chart-title">{title}</p>
      <canvas ref={ref} style={{ width:"100%", height:"200px", display:"block" }} />
      <div className="chart-legend">
        {data.slice(0,6).map((d, i) => (
          <div key={i} className="legend-item">
            <span className="legend-dot" style={{ background: COLORS[i % COLORS.length] }} />
            <span className="legend-label">{d.name}</span>
            <span className="legend-val">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Bar Chart ────────────────────────────────────────────────────────────────
function BarChart({ data, title, color = ACCENT, yLabel = "" }) {
  const ref = useCanvas((ctx, w, h) => {
    if (!data.length) return;
    const pad = { top: 20, right: 16, bottom: 36, left: 36 };
    const cw = w - pad.left - pad.right;
    const ch = h - pad.top  - pad.bottom;
    const max = Math.max(...data.map(d => d.value), 1);
    const bw = (cw / data.length) * 0.6;
    const gap = cw / data.length;

    // grid lines
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = pad.top + ch - (i / 4) * ch;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + cw, y); ctx.stroke();
    }

    data.forEach((d, i) => {
      const bh = (d.value / max) * ch;
      const x  = pad.left + i * gap + (gap - bw) / 2;
      const y  = pad.top  + ch - bh;

      // bar
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.85;
      const rad = 4;
      ctx.beginPath();
      ctx.moveTo(x + rad, y);
      ctx.lineTo(x + bw - rad, y);
      ctx.quadraticCurveTo(x + bw, y, x + bw, y + rad);
      ctx.lineTo(x + bw, y + bh);
      ctx.lineTo(x, y + bh);
      ctx.lineTo(x, y + rad);
      ctx.quadraticCurveTo(x, y, x + rad, y);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 1;

      // label
      ctx.fillStyle = "#8888aa";
      ctx.font = "10px 'DM Sans', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(d.label, x + bw / 2, pad.top + ch + 18);

      // value
      if (d.value > 0) {
        ctx.fillStyle = "#f0f0f5";
        ctx.font = "11px 'DM Sans', sans-serif";
        ctx.fillText(d.value, x + bw / 2, y - 6);
      }
    });
  }, [data, color]);

  return (
    <div className="chart-card">
      <p className="chart-title">{title}</p>
      <canvas ref={ref} style={{ width:"100%", height:"200px", display:"block" }} />
    </div>
  );
}

// ── Radar / Spider Chart ─────────────────────────────────────────────────────
function RadarChart({ data, title }) {
  const ref = useCanvas((ctx, w, h) => {
    if (!data.length) return;
    const cx = w / 2, cy = h / 2;
    const r  = Math.min(cx, cy) - 40;
    const n  = data.length;
    const step = (2 * Math.PI) / n;
    const toXY = (i, val) => ({
      x: cx + val * r * Math.cos(step * i - Math.PI / 2),
      y: cy + val * r * Math.sin(step * i - Math.PI / 2),
    });

    // grid rings
    for (let ring = 1; ring <= 4; ring++) {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const { x, y } = toXY(i, ring / 4);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = "rgba(255,255,255,0.07)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // axes
    for (let i = 0; i < n; i++) {
      const { x, y } = toXY(i, 1);
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(x, y);
      ctx.strokeStyle = "rgba(255,255,255,0.1)"; ctx.stroke();
    }

    // filled polygon
    ctx.beginPath();
    data.forEach((d, i) => {
      const { x, y } = toXY(i, d.value);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle   = "rgba(167,139,250,0.25)";
    ctx.strokeStyle = PURPLE;
    ctx.lineWidth   = 2;
    ctx.fill(); ctx.stroke();

    // dots + labels
    data.forEach((d, i) => {
      const { x, y } = toXY(i, d.value);
      ctx.beginPath(); ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fillStyle = PURPLE; ctx.fill();

      const lx = cx + (r + 22) * Math.cos(step * i - Math.PI / 2);
      const ly = cy + (r + 22) * Math.sin(step * i - Math.PI / 2);
      ctx.fillStyle = "#f0f0f5";
      ctx.font = "11px 'DM Sans', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(d.label, lx, ly);
    });
  }, [data]);

  return (
    <div className="chart-card">
      <p className="chart-title">{title}</p>
      <canvas ref={ref} style={{ width:"100%", height:"220px", display:"block" }} />
    </div>
  );
}

// ── Stat Pill ────────────────────────────────────────────────────────────────
function StatCard({ value, label, sub, color }) {
  return (
    <div className="stat-card">
      <span className="stat-card-val" style={{ color: color || ACCENT }}>{value}</span>
      <span className="stat-card-label">{label}</span>
      {sub && <span className="stat-card-sub">{sub}</span>}
    </div>
  );
}

// ── Main Stats Tab ───────────────────────────────────────────────────────────
export default function StatsTab({ watched }) {
  if (!watched.length) return (
    <div className="empty-watched">
      <p className="empty-icon">📊</p>
      <h3>No data yet</h3>
      <p>Mark some movies as watched to see your cinema stats</p>
    </div>
  );

  // ── Compute everything ──
  const rated   = watched.filter(m => m.userRating > 0);
  const avgUser = rated.length ? (rated.reduce((s,m)=>s+m.userRating,0)/rated.length).toFixed(1) : "—";
  const avgTmdb = (watched.reduce((s,m)=>s+(m.rating||0),0)/watched.length).toFixed(1);
  const topRated= rated.sort((a,b)=>b.userRating-a.userRating)[0];
  const newest  = [...watched].sort((a,b)=>new Date(b.watchedAt)-new Date(a.watchedAt))[0];

  // Genre donut
  const genreCount = {};
  watched.forEach(m => (m.genre_ids||[]).forEach(gid => {
    genreCount[gid] = (genreCount[gid]||0) + 1;
  }));
  const genreData = Object.entries(genreCount)
    .map(([id,v])=>({ name: GENRE_NAMES[id]||"Other", value:v }))
    .sort((a,b)=>b.value-a.value).slice(0,7);

  // Rating distribution bar
  const ratingDist = [1,2,3,4,5].map(r => ({
    label: "★".repeat(r),
    value: rated.filter(m=>m.userRating===r).length,
  }));

  // Monthly activity bar (last 6 months)
  const now = new Date();
  const monthData = Array.from({length:6},(_,i)=>{
    const d = new Date(now.getFullYear(), now.getMonth()-5+i, 1);
    const label = d.toLocaleString("default",{month:"short"});
    const value = watched.filter(m=>{
      const w = new Date(m.watchedAt);
      return w.getFullYear()===d.getFullYear() && w.getMonth()===d.getMonth();
    }).length;
    return { label, value };
  });

  // Radar: vibe DNA
  const dimTotals = { complexity:0, darkness:0, humor:0, action:0, emotion:0, suspense:0 };
  const GENRE_W = {
    28:{action:0.9,darkness:0.4},12:{action:0.6,emotion:0.5},16:{humor:0.5,emotion:0.6},
    35:{humor:0.9},80:{darkness:0.8,suspense:0.7},18:{emotion:0.8,complexity:0.5},
    27:{darkness:0.9,suspense:0.8},878:{complexity:0.9,suspense:0.6},
    53:{suspense:0.9,darkness:0.6},10749:{emotion:0.9},9648:{suspense:0.9,complexity:0.8},
  };
  watched.forEach(m=>{
    (m.genre_ids||[]).forEach(gid=>{
      if (GENRE_W[gid]) Object.entries(GENRE_W[gid]).forEach(([d,w])=>{ dimTotals[d]+=w; });
    });
  });
  const n = watched.length || 1;
  const radarData = [
    {label:"Complex",  value: Math.min(dimTotals.complexity/n,1)},
    {label:"Dark",     value: Math.min(dimTotals.darkness/n,1)},
    {label:"Funny",    value: Math.min(dimTotals.humor/n,1)},
    {label:"Action",   value: Math.min(dimTotals.action/n,1)},
    {label:"Emotional",value: Math.min(dimTotals.emotion/n,1)},
    {label:"Suspense", value: Math.min(dimTotals.suspense/n,1)},
  ];

  // TMDB score dist
  const tmdbDist = [
    {label:"1-3", value:watched.filter(m=>m.rating<4).length},
    {label:"4-5", value:watched.filter(m=>m.rating>=4&&m.rating<6).length},
    {label:"6-7", value:watched.filter(m=>m.rating>=6&&m.rating<8).length},
    {label:"7-8", value:watched.filter(m=>m.rating>=7&&m.rating<8).length},
    {label:"8+",  value:watched.filter(m=>m.rating>=8).length},
  ];

  return (
    <div className="stats-tab">
      {/* Top stat cards */}
      <div className="stat-cards-row">
        <StatCard value={watched.length} label="Movies Watched" color={ACCENT}/>
        <StatCard value={avgUser==="—"?avgUser:`${avgUser}/5`} label="Avg Your Rating" color={AMBER}/>
        <StatCard value={`${avgTmdb}/10`} label="Avg TMDB Score" color={CYAN}/>
        <StatCard value={rated.length} label="Movies Rated" color={GREEN}/>
        {topRated && <StatCard value={topRated.title.slice(0,14)+(topRated.title.length>14?"…":"")} label="Your Top Pick" sub={`★ ${topRated.userRating}/5`} color={PURPLE}/>}
      </div>

      {/* Charts row 1 */}
      <div className="charts-grid">
        <DonutChart data={genreData} title="🎭 Genre Breakdown"/>
        <RadarChart data={radarData} title="🧬 Your Vibe DNA"/>
        <BarChart   data={ratingDist} title="⭐ Your Rating Distribution" color={AMBER}/>
      </div>

      {/* Charts row 2 */}
      <div className="charts-grid">
        <BarChart data={monthData}  title="📅 Watching Activity (6 months)" color={CYAN}/>
        <BarChart data={tmdbDist}   title="📊 TMDB Score Distribution" color={PURPLE}/>
        <div className="chart-card recent-card">
          <p className="chart-title">🕐 Recently Watched</p>
          <div className="recent-list">
            {[...watched].sort((a,b)=>new Date(b.watchedAt)-new Date(a.watchedAt)).slice(0,5).map(m=>(
              <div key={m.id} className="recent-item">
                {m.poster
                  ? <img src={m.poster} className="recent-poster" alt={m.title}/>
                  : <div className="recent-poster no-poster-sm">🎬</div>}
                <div className="recent-info">
                  <p className="recent-title">{m.title}</p>
                  <p className="recent-meta">
                    {m.release_year} · TMDB {m.rating}
                    {m.userRating>0&&<span className="recent-stars"> · {"★".repeat(m.userRating)}</span>}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
