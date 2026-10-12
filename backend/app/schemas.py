from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):

    name: str

    email: EmailStr

    password: str

    confirmPassword: str


class UserResponse(BaseModel):

    id: int

    name: str

    email: EmailStr

    role: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):

    email: EmailStr

    password: str


class Token(BaseModel):

    access_token: str

    token_type: str


from typing import Optional, List
from datetime import datetime


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    agent_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatConversationSummary(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatConversationDetail(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"


class UpdateConversationRequest(BaseModel):
    title: str