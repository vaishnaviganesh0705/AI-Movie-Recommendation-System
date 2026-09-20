from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import auth
from app.routers import tmdb
from app.routers import watchlist
from app.routers import history
from app.routers import users
from app.routers import chat
from app.routers import notifications
from app.routers import subscription
from app.routers import music

from fastapi.staticfiles import StaticFiles
import app.models

app = FastAPI(
    title="StreamHub API",
    version="1.0.0"
)

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# =========================================================
# ROUTERS
# =========================================================

app.include_router(tmdb.router)
app.include_router(auth.router)
app.include_router(watchlist.router)
app.include_router(history.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(notifications.router)
app.include_router(subscription.router)
app.include_router(music.router)

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)

# =========================================================
# HEALTH / ROOT
# =========================================================

@app.get("/")
def home():
    return {
        "message": "StreamHub backend is running",
        "version": "1.0.0"
    }