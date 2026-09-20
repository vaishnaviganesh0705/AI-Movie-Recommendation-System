from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Artist(Base):
    __tablename__ = "artists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Album(Base):
    __tablename__ = "albums"
    id = Column(Integer, primary_key=True, index=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False)
    title = Column(String(255), nullable=False)
    cover_image_url = Column(String(255), nullable=True)
    release_date = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    artist = relationship("Artist")

class Song(Base):
    __tablename__ = "songs"
    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False)
    title = Column(String(255), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    genre = Column(String(100), nullable=True)
    audio_url = Column(String(255), nullable=True)
    popularity = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    
    artist = relationship("Artist")
    album = relationship("Album")

class Playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    cover_image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
class PlaylistSong(Base):
    __tablename__ = "playlist_songs"
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    added_at = Column(DateTime, server_default=func.now())

class LikedSong(Base):
    __tablename__ = "liked_songs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    liked_at = Column(DateTime, server_default=func.now())
