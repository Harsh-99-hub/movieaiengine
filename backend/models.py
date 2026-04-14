from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional, List
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Guest")
    watch_history = relationship("WatchHistory", back_populates="user", cascade="all, delete-orphan")
    genre_prefs = relationship("GenrePreference", back_populates="user", cascade="all, delete-orphan")


class WatchHistory(Base):
    __tablename__ = "watch_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    movie_id = Column(Integer, nullable=False)
    movie_title = Column(String, nullable=False)
    movie_poster = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    genres = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())
    user = relationship("User", back_populates="watch_history")


class GenrePreference(Base):
    __tablename__ = "genre_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    genre = Column(String, nullable=False)
    score = Column(Float, default=0.0)
    user = relationship("User", back_populates="genre_prefs")


class RateMovieRequest(BaseModel):
    user_id: int = 1
    movie_id: int
    movie_title: str
    movie_poster: Optional[str] = None
    rating: float
    genres: List[str] = []