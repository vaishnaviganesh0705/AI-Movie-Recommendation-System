from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
try:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    print("Database connected successfully!")
    connection.close()
except Exception as e:
    print(f"Database connection failed: {e}")
