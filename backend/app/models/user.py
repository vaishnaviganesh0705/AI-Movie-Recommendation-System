from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    avatar = Column(String(255), nullable=True)
    bio = Column(String(500), nullable=True)
    preferred_language = Column(String(50), default="en-US")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    conversations = relationship("ChatConversation", back_populates="user", cascade="all, delete-orphan")

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    preferred_genres = Column(String(255), nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=False)
    autoplay = Column(Boolean, default=True)
    adult_content_preference = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="preferences")
