import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from core.database import async_session, init_db
from core.security import hash_password
from models import (
    User, UserPhoto, UserPreferences, Swipe, Match, Message,
    BlockReport, Subscription,
)

FIRST_NAMES_M = ["Rahul", "Arjun", "Vikram", "Karan", "Amit", "Siddharth", "Rohan", "Aditya", "Nikhil", "Deepak"]
FIRST_NAMES_F = ["Priya", "Ananya", "Neha", "Riya", "Kavya", "Shreya", "Meera", "Ishita", "Pooja", "Sanya"]
LAST_NAMES = ["Sharma", "Patel", "Singh", "Kumar", "Verma", "Gupta", "Reddy", "Nair", "Joshi", "Mehta"]
CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]
INTENTS = ["lets_see", "serious_relationship", "casual", "friendship", "marriage"]
BIOS = [
    "Love traveling and trying new cuisines.",
    "Dog person, coffee addict, looking for genuine connections.",
    "Into fitness, music, and late-night conversations.",
    "Engineer by day, dreamer by night.",
    "Looking for someone who can match my energy.",
    "Foodie, bookworm, and occasional dancer.",
    "Exploring life one city at a time.",
    "Simple living, high thinking.",
]
LANGUAGES = ["en", "hi", "te", "ta", "mr", "bn", "gu", "kn", "ml"]
MESSAGE_TEXTS = [
    "Hey, how are you?",
    "Loved your profile!",
    "What's up?",
    "How was your day?",
    "Nice to meet you here!",
    "You seem interesting.",
    "Any plans for the weekend?",
    "What kind of music do you like?",
    "Have you been to this cafe before?",
    "Your bio caught my eye.",
    "Hi there!",
    "Hello, how's it going?",
    "Love the vibe of your profile.",
    "Fellow foodie here!",
    "Your photos are amazing!",
]


def rand_dt(days_ago_max=30):
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


async def generate():
    await init_db()

    async with async_session() as db:
        existing = (await db.execute(select(User).where(User.phone_number != "0000000000"))).scalars().all()
        if existing:
            print(f"Dummy data already exists ({len(existing)} users). Skipping.")
            return

        # ── Create users ──
        users = []
        user_ids = []

        # 10 male users
        for i in range(10):
            name = f"{random.choice(FIRST_NAMES_M)} {random.choice(LAST_NAMES)}"
            u = User(
                phone_number=f"99900010{str(i).zfill(2)}",
                phone_verified=True,
                password_hash=hash_password("test123"),
                name=name,
                date_of_birth=f"{random.randint(1990, 2002)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                gender="male",
                bio=random.choice(BIOS),
                intent=random.choice(INTENTS),
                city=random.choice(CITIES),
                profile_complete=True,
                is_active=True,
                photo_verified=random.choice([True, False]),
                is_premium=random.choice([True, False, False]),
                created_at=rand_dt(90),
                last_active=rand_dt(3),
            )
            db.add(u)
            users.append(u)
            # Add photos after flush to get user.id
            await db.flush()
            for j in range(random.randint(1, 3)):
                db.add(UserPhoto(
                    user_id=u.id,
                    photo_url=f"https://picsum.photos/seed/{u.name.replace(' ', '')}{j}/400/600",
                    is_primary=(j == 0),
                    sort_order=j,
                ))

        # 10 female users
        for i in range(10):
            name = f"{random.choice(FIRST_NAMES_F)} {random.choice(LAST_NAMES)}"
            u = User(
                phone_number=f"99900020{str(i).zfill(2)}",
                phone_verified=True,
                password_hash=hash_password("test123"),
                name=name,
                date_of_birth=f"{random.randint(1990, 2002)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                gender="female",
                bio=random.choice(BIOS),
                intent=random.choice(INTENTS),
                city=random.choice(CITIES),
                profile_complete=True,
                is_active=True,
                photo_verified=random.choice([True, False]),
                is_premium=random.choice([True, False, False]),
                created_at=rand_dt(90),
                last_active=rand_dt(3),
            )
            db.add(u)
            users.append(u)
            await db.flush()
            for j in range(random.randint(1, 3)):
                db.add(UserPhoto(
                    user_id=u.id,
                    photo_url=f"https://picsum.photos/seed/{u.name.replace(' ', '')}{j}/400/600",
                    is_primary=(j == 0),
                    sort_order=j,
                ))

        await db.flush()
        user_ids = [u.id for u in users]
        print(f"Created {len(users)} users.")

        # ── Create preferences for each user ──
        for u in users:
            pref = UserPreferences(
                user_id=u.id,
                min_age=18,
                max_age=random.choice([35, 40, 45, 50]),
                preferred_gender="female" if u.gender == "male" else "male",
                max_distance_km=random.choice([25, 50, 75, 100]),
            )
            db.add(pref)
        await db.flush()
        print("Created user preferences.")

        # ── Create swipes (likes crossing gender lines) ──
        males = [u for u in users if u.gender == "male"]
        females = [u for u in users if u.gender == "female"]
        swipes_created = 0
        for m in males:
            for f in random.sample(females, min(5, len(females))):
                db.add(Swipe(swiper_id=m.id, swiped_id=f.id, direction="like", created_at=rand_dt(60)))
                swipes_created += 1
        for f in females:
            for m in random.sample(males, min(5, len(males))):
                db.add(Swipe(swiper_id=f.id, swiped_id=m.id, direction="like", created_at=rand_dt(60)))
                swipes_created += 1
        await db.flush()
        print(f"Created {swipes_created} swipes.")

        # ── Create matches (mutual likes) ──
        # Build a set of mutual like pairs
        likes = (await db.execute(select(Swipe).where(Swipe.direction == "like"))).scalars().all()
        like_map = {}  # swiper_id -> set of swiped_ids
        for s in likes:
            like_map.setdefault(s.swiper_id, set()).add(s.swiped_id)

        matches_created = 0
        matches_list = []
        for swiper_id, swiped_set in like_map.items():
            for swiped_id in swiped_set:
                if swiper_id < swiped_id:
                    swiped_set_other = like_map.get(swiped_id)
                    if swiped_set_other and swiper_id in swiped_set_other:
                        m = Match(
                            user1_id=swiper_id,
                            user2_id=swiped_id,
                            matched_at=rand_dt(30),
                            is_active=True,
                        )
                        db.add(m)
                        matches_list.append(m)
                        matches_created += 1
        await db.flush()
        print(f"Created {matches_created} matches.")

        # ── Create messages for matches ──
        messages_created = 0
        for match in matches_list:
            participants = [match.user1_id, match.user2_id]
            num_msgs = random.randint(3, 15)
            base_time = match.matched_at or datetime.now(timezone.utc)
            for i in range(num_msgs):
                sender = random.choice(participants)
                msg = Message(
                    match_id=match.id,
                    sender_id=sender,
                    message_type="text",
                    content=random.choice(MESSAGE_TEXTS),
                    is_read=random.choice([True, True, True, False]),
                    created_at=base_time + timedelta(minutes=random.randint(5, 60 * 24 * 7)),
                )
                db.add(msg)
                messages_created += 1
        await db.flush()
        print(f"Created {messages_created} messages.")

        # ── Create a few reports ──
        for _ in range(3):
            reporter = random.choice(users)
            reported = random.choice([u for u in users if u.id != reporter.id])
            db.add(BlockReport(
                reporter_id=reporter.id,
                reported_id=reported.id,
                reason=random.choice(["Inappropriate behavior", "Fake profile", "Spam"]),
                type="report",
                created_at=rand_dt(14),
            ))
        print("Created 3 reports.")

        # ── Create a few subscriptions ──
        premium_users = [u for u in users if u.is_premium]
        for u in premium_users[:5]:
            start = rand_dt(60)
            db.add(Subscription(
                user_id=u.id,
                plan_type=random.choice(["monthly", "yearly"]),
                starts_at=start,
                ends_at=start + timedelta(days=30 if random.random() > 0.5 else 365),
                is_active=True,
            ))
        print(f"Created subscriptions for premium users.")

        await db.commit()
        print("\nDummy data generated successfully!")
        print(f"  Users:         {len(users)}")
        print(f"  Matches:       {matches_created}")
        print(f"  Messages:      {messages_created}")
        print(f"  Swipes:        {swipes_created}")
        print(f"  Login:         any phone 99900010xx / test123")


if __name__ == "__main__":
    asyncio.run(generate())
