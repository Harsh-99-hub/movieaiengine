from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routers import search, movies, vibe, recommend

# Create app
app = FastAPI(
    title="MovieAI API",
    version="3.0.0"
)

# ✅ CORS (FIXED FOR VERCEL + LOCAL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://movieaiengine.vercel.app",  # 🔥 your deployed frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Routers (ALL under /api)
app.include_router(search.router, prefix="/api")
app.include_router(movies.router, prefix="/api")
app.include_router(vibe.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")

# ✅ Root route
@app.get("/")
def root():
    return {
        "message": "MovieAI API v3 — Intelligent Movie Discovery 🎬"
    }