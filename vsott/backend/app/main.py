from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth
from app.routers import tmdb
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
        "http://127.0.0.1:5173"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# =========================================================
# TMDB ROUTER
# =========================================================

app.include_router(
    tmdb.router
)
app.include_router(auth.router)

# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "StreamHub backend is running"
    }