import os
from dotenv import load_dotenv
load_dotenv()
from app.database import engine, Base

print("Importing all models to bind metadata...")
from app.models.user import User, UserPreferences
from app.models.content import Content
from app.models.music import Artist, Album, Song, Playlist, PlaylistSong, LikedSong
from app.models.activity import Watchlist, WatchHistory, Rating, UserActivity
from app.models.notification import Notification
from app.models.subscription import SubscriptionPlan, UserSubscription, Payment

print(f"Registered tables: {list(Base.metadata.tables.keys())}")

try:
    print("Executing create_all()...")
    Base.metadata.create_all(bind=engine)
    print("Execution complete.")
except Exception as e:
    print(f"FAILED TO CREATE: {str(e)}")
