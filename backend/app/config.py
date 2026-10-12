import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend/.env is reliably loaded regardless of current working directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")

if TMDB_ACCESS_TOKEN:
    TMDB_ACCESS_TOKEN = TMDB_ACCESS_TOKEN.strip().strip("'\"")

print("TMDB TOKEN FOUND:", "Yes" if TMDB_ACCESS_TOKEN else "No")