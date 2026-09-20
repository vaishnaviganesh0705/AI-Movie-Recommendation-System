from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Watchlist
from pydantic import BaseModel
from typing import Optional, List
import datetime

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

class WatchlistItemCreate(BaseModel):
    tmdb_id: int
    content_type: str 

class WatchlistItemResponse(BaseModel):
    id: int
    tmdb_id: int
    content_type: str
    added_at: datetime.datetime
    
    class Config:
        from_attributes = True

@router.post("", response_model=WatchlistItemResponse)
def add_to_watchlist(item: WatchlistItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.tmdb_id == item.tmdb_id,
        Watchlist.content_type == item.content_type
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Item already in watchlist")
        
    new_item = Watchlist(
        user_id=current_user.id,
        tmdb_id=item.tmdb_id,
        content_type=item.content_type
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.get("", response_model=List[WatchlistItemResponse])
def get_watchlist(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    return items

@router.delete("/{tmdb_id}")
def remove_from_watchlist(tmdb_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.tmdb_id == tmdb_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in watchlist")
        
    db.delete(item)
    db.commit()
    return {"message": "Success"}
