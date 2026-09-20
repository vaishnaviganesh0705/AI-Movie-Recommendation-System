from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.subscription import UserSubscription, SubscriptionPlan
from pydantic import BaseModel
from typing import Optional
import shutil
import base64
import os
from uuid import uuid4
import datetime


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# =========================================================
# PROFILE UPDATE
# =========================================================

class ProfileUpdate(BaseModel):
    name: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
    preferred_language: Optional[str] = None


# =========================================================
# PROFILE RESPONSE
# =========================================================

class ProfileResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    avatar: Optional[str]
    bio: Optional[str]
    preferred_language: Optional[str]

    class Config:
        from_attributes = True


# =========================================================
# GET MY PROFILE
# =========================================================

@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


# =========================================================
# UPDATE PROFILE
# =========================================================

@router.put("/me", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.name = data.name
    current_user.bio = data.bio
    current_user.avatar = data.avatar

    if data.preferred_language:
        current_user.preferred_language = data.preferred_language

    db.commit()
    db.refresh(current_user)

    return current_user


# =========================================================
# GET MY SUBSCRIPTION
# =========================================================

@router.get("/me/subscription")
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).first()

    if not subscription:
        return {
            "plan_name": "Free",
            "plan_price": 0.0,
            "status": "none"
        }

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == subscription.plan_id
    ).first()

    return {
        "id": subscription.id,
        "status": subscription.status,
        "expires_at": subscription.expires_at,
        "plan_name": plan.name if plan else "Unknown",
        "plan_price": plan.price if plan else 0.0,
        "features": plan.features if plan else None
    }


# =========================================================
# AVATAR UPLOAD MODEL
# =========================================================

class AvatarUpload(BaseModel):
    avatar_base64: str


# =========================================================
# UPLOAD AVATAR
# =========================================================

@router.post("/avatar")
def upload_avatar(
    data: AvatarUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    header, encoded = data.avatar_base64.split(",", 1)

    file_extension = header.split("/")[1].split(";")[0]

    if file_extension == "jpeg":
        file_extension = "jpg"

    filename = f"{uuid4()}.{file_extension}"

    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(base64.b64decode(encoded))

    current_user.avatar = f"http://127.0.0.1:8000/uploads/{filename}"

    db.commit()
    db.refresh(current_user)

    return {
        "avatar": current_user.avatar
    }