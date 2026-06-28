import asyncio
from sqlalchemy import select
from core.database import async_session, init_db, engine
from core.security import hash_password
from models import User, Plan, UserPreferences
from datetime import datetime, timezone


DEFAULT_PHONE = "0000000000"
DEFAULT_PASSWORD = "admin123"
DEFAULT_NAME = "Admin"

DEFAULT_PLANS = [
    {"name": "Free", "price_paise": 0, "duration_days": 0, "sort_order": 0},
    {"name": "Premium Monthly", "price_paise": 49900, "duration_days": 30, "sort_order": 1},
    {"name": "Premium Yearly", "price_paise": 299900, "duration_days": 365, "sort_order": 2},
]


async def seed():
    await init_db()

    async with async_session() as db:
        plans_exist = (await db.execute(select(Plan))).scalars().first()
        if not plans_exist:
            for p in DEFAULT_PLANS:
                db.add(Plan(**p))
            await db.flush()
            print("Default subscription plans created.")

        result = await db.execute(select(User).where(User.phone_number == DEFAULT_PHONE))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Default account already exists (phone: {DEFAULT_PHONE})")
        else:
            user = User(
                phone_number=DEFAULT_PHONE,
                phone_verified=True,
                password_hash=hash_password(DEFAULT_PASSWORD),
                name=DEFAULT_NAME,
                date_of_birth="2000-01-01",
                gender="male",
                city="Mumbai",
                profile_complete=True,
                is_premium=True,
                photo_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(user)
            await db.flush()
            print("Default account created:")
            print(f"  Phone:    {DEFAULT_PHONE}")
            print(f"  Password: {DEFAULT_PASSWORD}")
            existing = user

        # Ensure admin has preferences
        pref_result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == existing.id)
        )
        if not pref_result.scalar_one_or_none():
            db.add(UserPreferences(
                user_id=existing.id,
                min_age=18,
                max_age=50,
                preferred_gender="all",
                max_distance_km=500,
            ))
            print("Admin preferences created (all genders, 18-50, 500km).")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
