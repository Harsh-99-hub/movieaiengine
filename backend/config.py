from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TMDB_API_KEY: str
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE: str = "https://image.tmdb.org/t/p/w500"
    DATABASE_URL: str = "sqlite+aiosqlite:///./movie_ai.db"
    DEFAULT_USER_ID: int = 1
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()