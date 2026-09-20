from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.sql import func
from app.database import Base

class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("content.id"), nullable=True)
    tmdb_id = Column(Integer, nullable=True)
    content_type = Column(String(50), nullable=True) 
    added_at = Column(DateTime, server_default=func.now())

class WatchHistory(Base):
    __tablename__ = "watch_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("content.id"), nullable=True)
    tmdb_id = Column(Integer, nullable=True)
    content_type = Column(String(50), nullable=True)
    progress_seconds = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    last_watched_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("content.id"), nullable=True)
    tmdb_id = Column(Integer, nullable=True)
    rating = Column(Numeric(3,1), nullable=False)
    review = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class UserActivity(Base):
    __tablename__ = "user_activity"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(String(100), nullable=False)
    content_id = Column(Integer, nullable=True)
    music_id = Column(Integer, nullable=True)
    metadata_info = Column(Text, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
