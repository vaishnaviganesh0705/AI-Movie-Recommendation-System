from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric
from sqlalchemy.sql import func
from app.database import Base

class Content(Base):
    __tablename__ = "content"
    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1500), nullable=True)
    poster_path = Column(String(255), nullable=True)
    backdrop_path = Column(String(255), nullable=True)
    release_date = Column(Date, nullable=True)
    language = Column(String(50), nullable=True)
    genres = Column(String(255), nullable=True)
    runtime = Column(Integer, nullable=True)
    rating = Column(Numeric(4, 2), nullable=True)
    content_type = Column(String(50), nullable=False) # 'movie' or 'tv_show'
    trailer_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
