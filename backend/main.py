from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import search, movies, vibe, recommend

app = FastAPI(title="MovieAI API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api")
app.include_router(movies.router, prefix="/api")
app.include_router(vibe.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "MovieAI API v3 — Intelligent Movie Discovery 🎬"}