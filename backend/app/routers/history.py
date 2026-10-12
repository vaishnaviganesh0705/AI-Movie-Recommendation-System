from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, WatchHistory
from pydantic import BaseModel
from typing import Optional, List
import datetime

router = APIRouter(prefix="/history", tags=["History"])

class HistoryItemCreate(BaseModel):
    tmdb_id: int
    content_type: str
    progress_seconds: int
    duration_seconds: int
    completed: bool

class HistoryItemResponse(BaseModel):
    id: int
    tmdb_id: int
    content_type: str
    progress_seconds: int
    duration_seconds: int
    completed: bool
    last_watched_at: datetime.datetime
    
    class Config:
        from_attributes = True

@router.post("", response_model=HistoryItemResponse)
def update_history(item: HistoryItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    history_item = db.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id,
        WatchHistory.tmdb_id == item.tmdb_id
    ).first()
    
    if not history_item:
        history_item = WatchHistory(
            user_id=current_user.id,
            tmdb_id=item.tmdb_id,
            content_type=item.content_type
        )
        db.add(history_item)
        
    history_item.progress_seconds = item.progress_seconds
    history_item.duration_seconds = item.duration_seconds
    history_item.completed = item.completed
    history_item.last_watched_at = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(history_item)
    return history_item

@router.get("", response_model=List[HistoryItemResponse])
def get_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(WatchHistory).filter(WatchHistory.user_id == current_user.id).order_by(WatchHistory.last_watched_at.desc()).all()
    return items

@router.delete("/{tmdb_id}")
def remove_from_history(tmdb_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(WatchHistory).filter(
        WatchHistory.user_id == current_user.id,
        WatchHistory.tmdb_id == tmdb_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Success"}
