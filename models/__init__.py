from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from ..core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    phone_verified = Column(Boolean, default=False)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    date_of_birth = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    intent = Column(String, default="lets_see")
    city = Column(String, nullable=False, index=True)
    college = Column(String, nullable=True)
    workplace = Column(String, nullable=True)
    height_cm = Column(Integer, nullable=True)
    religion = Column(String, nullable=True)
    education = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    photo_verified = Column(Boolean, default=False)
    profile_complete = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_active = Column(DateTime, nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    preferred_language = Column(String, default="en")
    show_online_status = Column(Boolean, default=True)
    show_distance = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    photos = relationship("UserPhoto", back_populates="user", cascade="all, delete-orphan")
    languages = relationship("UserLanguage", back_populates="user", cascade="all, delete-orphan")
    voice_prompts = relationship("VoicePrompt", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    swipes_made = relationship("Swipe", foreign_keys="Swipe.swiper_id", back_populates="swiper", cascade="all, delete-orphan")
    swipes_received = relationship("Swipe", foreign_keys="Swipe.swiped_id", back_populates="swiped", cascade="all, delete-orphan")


class UserPhoto(Base):
    __tablename__ = "user_photos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="photos")


class UserLanguage(Base):
    __tablename__ = "user_languages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language = Column(String, nullable=False)
    user = relationship("User", back_populates="languages")


class VoicePrompt(Base):
    __tablename__ = "voice_prompts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_question = Column(String, nullable=False)
    audio_url = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="voice_prompts")


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_age = Column(Integer, default=18)
    max_age = Column(Integer, default=50)
    preferred_gender = Column(String, default="all")
    max_distance_km = Column(Integer, default=50)
    intent_filter = Column(String, nullable=True)
    city_filter = Column(String, nullable=True)
    user = relationship("User", back_populates="preferences")


class Swipe(Base):
    __tablename__ = "swipes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    swiper_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    swiped_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    direction = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("swiper_id", "swiped_id", name="uq_swipe_pair"),)
    swiper = relationship("User", foreign_keys=[swiper_id], back_populates="swipes_made")
    swiped = relationship("User", foreign_keys=[swiped_id], back_populates="swipes_received")


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    matched_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    unmatched_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    __table_args__ = (
        CheckConstraint("user1_id < user2_id", name="ck_match_order"),
        UniqueConstraint("user1_id", "user2_id", name="uq_match_pair"),
    )
    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(String, default="text")
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    match = relationship("Match", back_populates="messages")
    sender = relationship("User")


class BlockReport(Base):
    __tablename__ = "blocks_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String, nullable=True)
    type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("reporter_id", "reported_id", "type", name="uq_block_report"),)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    related_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FamilyShare(Base):
    __tablename__ = "family_shares"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_with_email = Column(String, nullable=True)
    shared_with_phone = Column(String, nullable=True)
    access_token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_type = Column(String, nullable=False)
    starts_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
