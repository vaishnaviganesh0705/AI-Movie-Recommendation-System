import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")

if TMDB_ACCESS_TOKEN:
    TMDB_ACCESS_TOKEN = TMDB_ACCESS_TOKEN.strip()

print("TMDB TOKEN FOUND:", "Yes" if TMDB_ACCESS_TOKEN else "No")