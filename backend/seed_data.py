import os
import datetime
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal, engine, Base
from app.models.subscription import SubscriptionPlan
from app.models.music import Artist, Album, Song


def seed_database():
    print("Starting database seeding...")
    db = SessionLocal()

    try:
        # 1. Seed Subscription Plans if not present
        existing_plans = db.query(SubscriptionPlan).count()
        if existing_plans == 0:
            print("Seeding Subscription Plans...")
            plans = [
                SubscriptionPlan(
                    id=1,
                    name="Free Tier",
                    price=0.00,
                    duration_days=365,
                    features="Standard definition (480p), Ad-supported, 1 screen, Limited library"
                ),
                SubscriptionPlan(
                    id=2,
                    name="Standard HD",
                    price=9.99,
                    duration_days=30,
                    features="Full HD (1080p), Ad-free streaming, 2 screens simultaneous, Offline downloads"
                ),
                SubscriptionPlan(
                    id=3,
                    name="Premium 4K Ultra",
                    price=19.99,
                    duration_days=30,
                    features="Ultra HD 4K + HDR, Dolby Atmos audio, 4 screens, VIP early access, Priority AI assistance"
                )
            ]
            db.bulk_save_objects(plans)
            db.commit()
            print("Subscription Plans seeded successfully.")
        else:
            print(f"Subscription Plans already exist ({existing_plans} found).")

        # 2. Seed Artists, Albums, and Songs if not present
        existing_songs = db.query(Song).count()
        if existing_songs == 0:
            print("Seeding Artists, Albums, and Songs...")

            # Reliable high-speed sample audio previews
            audio_samples = [
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3",
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3"
            ]

            artists_data = [
                {
                    "name": "Hans Zimmer",
                    "image": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&auto=format&fit=crop&q=60",
                    "albums": [
                        {
                            "title": "Interstellar (Original Soundtrack)",
                            "cover": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Cornfield Chase", "duration": 126, "genre": "Soundtrack", "pop": 98},
                                {"title": "No Time for Caution", "duration": 246, "genre": "Soundtrack", "pop": 95},
                                {"title": "Stay", "duration": 412, "genre": "Soundtrack", "pop": 92}
                            ]
                        },
                        {
                            "title": "Inception (Music from the Motion Picture)",
                            "cover": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Time", "duration": 275, "genre": "Soundtrack", "pop": 99},
                                {"title": "Dream Is Collapsing", "duration": 143, "genre": "Soundtrack", "pop": 90}
                            ]
                        }
                    ]
                },
                {
                    "name": "A. R. Rahman",
                    "image": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=500&auto=format&fit=crop&q=60",
                    "albums": [
                        {
                            "title": "Roja & Dil Se (Classics)",
                            "cover": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Chinna Chinna Aasai", "duration": 295, "genre": "Indian Classical", "pop": 96},
                                {"title": "Chaiyya Chaiyya", "duration": 394, "genre": "Bollywood", "pop": 98},
                                {"title": "Dil Se Re", "duration": 348, "genre": "World", "pop": 94}
                            ]
                        },
                        {
                            "title": "Slumdog Millionaire (Soundtrack)",
                            "cover": "https://images.unsplash.com/photo-1487180144351-b8472da7d491?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Jai Ho", "duration": 319, "genre": "Soundtrack", "pop": 97},
                                {"title": "Mausam & Escape", "duration": 233, "genre": "Instrumental", "pop": 88}
                            ]
                        }
                    ]
                },
                {
                    "name": "Anirudh Ravichander",
                    "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=500&auto=format&fit=crop&q=60",
                    "albums": [
                        {
                            "title": "Leo & Vikram OST",
                            "cover": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Badass", "duration": 229, "genre": "Tamil Rock", "pop": 99},
                                {"title": "Naa Ready", "duration": 248, "genre": "Tamil Pop", "pop": 98},
                                {"title": "Vikram Title Track", "duration": 218, "genre": "Electronic", "pop": 97}
                            ]
                        },
                        {
                            "title": "Jailer (Original Motion Picture)",
                            "cover": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Hukum - Thalaivar Alappara", "duration": 207, "genre": "Tamil Rock", "pop": 99},
                                {"title": "Kaavaalaa", "duration": 190, "genre": "Dance", "pop": 96}
                            ]
                        }
                    ]
                },
                {
                    "name": "Coldplay",
                    "image": "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=500&auto=format&fit=crop&q=60",
                    "albums": [
                        {
                            "title": "A Rush of Blood to the Head",
                            "cover": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "The Scientist", "duration": 309, "genre": "Alternative Rock", "pop": 97},
                                {"title": "Clocks", "duration": 307, "genre": "Alternative Rock", "pop": 95},
                                {"title": "Yellow", "duration": 269, "genre": "Alternative Rock", "pop": 98}
                            ]
                        }
                    ]
                },
                {
                    "name": "The Weeknd",
                    "image": "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=500&auto=format&fit=crop&q=60",
                    "albums": [
                        {
                            "title": "After Hours",
                            "cover": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Blinding Lights", "duration": 200, "genre": "Synthwave", "pop": 100},
                                {"title": "Save Your Tears", "duration": 215, "genre": "Synthpop", "pop": 97},
                                {"title": "In Your Eyes", "duration": 237, "genre": "Pop", "pop": 93}
                            ]
                        }
                    ]
                },
                {
                    "name": "Daft Punk",
                    "image": "https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=500&auto=format&fit=crop&q=60",
                    "albums": [
                        {
                            "title": "Random Access Memories",
                            "cover": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=500&auto=format&fit=crop&q=60",
                            "songs": [
                                {"title": "Get Lucky", "duration": 248, "genre": "Electronic", "pop": 98},
                                {"title": "Instant Crush", "duration": 337, "genre": "Electronic", "pop": 94},
                                {"title": "Lose Yourself to Dance", "duration": 353, "genre": "Funk", "pop": 90}
                            ]
                        }
                    ]
                }
            ]

            audio_idx = 0
            for art in artists_data:
                artist_obj = Artist(name=art["name"], image_url=art["image"])
                db.add(artist_obj)
                db.commit()
                db.refresh(artist_obj)

                for alb in art["albums"]:
                    album_obj = Album(
                        artist_id=artist_obj.id,
                        title=alb["title"],
                        cover_image_url=alb["cover"],
                        release_date=datetime.date(2022, 1, 1)
                    )
                    db.add(album_obj)
                    db.commit()
                    db.refresh(album_obj)

                    for s in alb["songs"]:
                        song_obj = Song(
                            album_id=album_obj.id,
                            artist_id=artist_obj.id,
                            title=s["title"],
                            duration_seconds=s["duration"],
                            genre=s["genre"],
                            audio_url=audio_samples[audio_idx % len(audio_samples)],
                            popularity=s["pop"]
                        )
                        db.add(song_obj)
                        audio_idx += 1

            db.commit()
            print("Music seeded successfully.")
        else:
            print(f"Music already exists ({existing_songs} songs found).")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
