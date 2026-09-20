from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.music import Artist, Album, Song, LikedSong, Playlist

router = APIRouter(prefix="/music", tags=["Music"])


# =========================================================
# GET SONGS (FILTERABLE)
# =========================================================

@router.get("/songs")
def get_songs(
    genre: Optional[str] = None,
    search: Optional[str] = None,
    artist_id: Optional[int] = None,
    album_id: Optional[int] = None,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Song)

    if genre and genre.lower() != "all":
        query = query.filter(Song.genre.ilike(f"%{genre}%"))

    if search:
        query = query.filter(Song.title.ilike(f"%{search}%"))

    if artist_id:
        query = query.filter(Song.artist_id == artist_id)

    if album_id:
        query = query.filter(Song.album_id == album_id)

    songs = query.order_by(Song.popularity.desc()).limit(limit).all()

    result = []
    for s in songs:
        result.append({
            "id": s.id,
            "title": s.title,
            "duration_seconds": s.duration_seconds,
            "genre": s.genre,
            "audio_url": s.audio_url,
            "popularity": s.popularity,
            "artist_id": s.artist_id,
            "artist_name": s.artist.name if s.artist else "Unknown Artist",
            "artist_image": s.artist.image_url if s.artist else None,
            "album_id": s.album_id,
            "album_title": s.album.title if s.album else "Single",
            "cover_image": s.album.cover_image_url if s.album else (s.artist.image_url if s.artist else None)
        })

    return result


# =========================================================
# GET ARTISTS
# =========================================================

@router.get("/artists")
def get_artists(
    search: Optional[str] = None,
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Artist)
    if search:
        query = query.filter(Artist.name.ilike(f"%{search}%"))
    
    artists = query.limit(limit).all()
    result = []
    for a in artists:
        songs_count = db.query(Song).filter(Song.artist_id == a.id).count()
        albums_count = db.query(Album).filter(Album.artist_id == a.id).count()
        result.append({
            "id": a.id,
            "name": a.name,
            "image_url": a.image_url,
            "songs_count": songs_count,
            "albums_count": albums_count
        })
    return result


# =========================================================
# GET ARTIST DETAILS WITH DISCOGRAPHY
# =========================================================

@router.get("/artists/{artist_id}")
def get_artist(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    albums = db.query(Album).filter(Album.artist_id == artist_id).all()
    songs = db.query(Song).filter(Song.artist_id == artist_id).order_by(Song.popularity.desc()).all()

    return {
        "id": artist.id,
        "name": artist.name,
        "image_url": artist.image_url,
        "albums": [
            {
                "id": alb.id,
                "title": alb.title,
                "cover_image_url": alb.cover_image_url,
                "release_date": str(alb.release_date) if alb.release_date else None
            }
            for alb in albums
        ],
        "top_tracks": [
            {
                "id": s.id,
                "title": s.title,
                "duration_seconds": s.duration_seconds,
                "genre": s.genre,
                "audio_url": s.audio_url,
                "popularity": s.popularity,
                "album_title": s.album.title if s.album else "Single",
                "cover_image": s.album.cover_image_url if s.album else artist.image_url
            }
            for s in songs
        ]
    }


# =========================================================
# GET ALBUMS
# =========================================================

@router.get("/albums")
def get_albums(
    search: Optional[str] = None,
    artist_id: Optional[int] = None,
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Album)
    if search:
        query = query.filter(Album.title.ilike(f"%{search}%"))
    if artist_id:
        query = query.filter(Album.artist_id == artist_id)

    albums = query.limit(limit).all()
    result = []
    for alb in albums:
        result.append({
            "id": alb.id,
            "title": alb.title,
            "cover_image_url": alb.cover_image_url,
            "artist_id": alb.artist_id,
            "artist_name": alb.artist.name if alb.artist else "Unknown Artist",
            "release_date": str(alb.release_date) if alb.release_date else None
        })
    return result


# =========================================================
# GET ALBUM DETAILS WITH TRACKS
# =========================================================

@router.get("/albums/{album_id}")
def get_album(album_id: int, db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    songs = db.query(Song).filter(Song.album_id == album_id).all()
    return {
        "id": album.id,
        "title": album.title,
        "cover_image_url": album.cover_image_url,
        "artist_id": album.artist_id,
        "artist_name": album.artist.name if album.artist else "Unknown Artist",
        "release_date": str(album.release_date) if album.release_date else None,
        "tracks": [
            {
                "id": s.id,
                "title": s.title,
                "duration_seconds": s.duration_seconds,
                "audio_url": s.audio_url,
                "genre": s.genre,
                "artist_name": album.artist.name if album.artist else "Unknown Artist"
            }
            for s in songs
        ]
    }


# =========================================================
# GET GENRES
# =========================================================

@router.get("/genres")
def get_music_genres(db: Session = Depends(get_db)):
    genres = db.query(Song.genre).distinct().all()
    unique_genres = sorted(list({g[0] for g in genres if g[0]}))
    return ["All"] + unique_genres


# =========================================================
# USER LIKED SONGS
# =========================================================

@router.get("/liked")
def get_liked_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    liked = db.query(LikedSong).filter(LikedSong.user_id == current_user.id).all()
    song_ids = [l.song_id for l in liked]
    if not song_ids:
        return []

    songs = db.query(Song).filter(Song.id.in_(song_ids)).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "duration_seconds": s.duration_seconds,
            "genre": s.genre,
            "audio_url": s.audio_url,
            "artist_name": s.artist.name if s.artist else "Unknown Artist",
            "album_title": s.album.title if s.album else "Single",
            "cover_image": s.album.cover_image_url if s.album else (s.artist.image_url if s.artist else None)
        }
        for s in songs
    ]


@router.post("/liked/{song_id}")
def toggle_like_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(LikedSong).filter(
        LikedSong.user_id == current_user.id,
        LikedSong.song_id == song_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"liked": False, "message": "Song removed from liked tracks"}
    else:
        new_liked = LikedSong(user_id=current_user.id, song_id=song_id)
        db.add(new_liked)
        db.commit()
        return {"liked": True, "message": "Song added to liked tracks"}
