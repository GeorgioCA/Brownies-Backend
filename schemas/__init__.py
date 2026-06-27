from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Auth ──

class SendOtpRequest(BaseModel):
    phone_number: str = Field(min_length=10, max_length=15)


class VerifyOtpRequest(BaseModel):
    phone_number: str
    otp: str


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Profile ──

class SetupProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    date_of_birth: str
    gender: str
    intent: str = "lets_see"
    city: str
    bio: Optional[str] = None
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    languages: list[str] = []
    preferred_language: str = "en"


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    intent: Optional[str] = None
    city: Optional[str] = None
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    preferred_language: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None


class UpdateLanguagesRequest(BaseModel):
    languages: list[str]


class ReorderPhotosRequest(BaseModel):
    photo_ids: list[int]


class VoicePromptCreate(BaseModel):
    prompt_question: str
    duration_seconds: Optional[int] = None


class UserLanguageOut(BaseModel):
    language: str
    model_config = {"from_attributes": True}


class UserPhotoOut(BaseModel):
    id: int
    photo_url: str
    is_primary: bool
    sort_order: int
    model_config = {"from_attributes": True}


class VoicePromptOut(BaseModel):
    id: int
    prompt_question: str
    audio_url: str
    duration_seconds: Optional[int] = None
    model_config = {"from_attributes": True}


class UserProfileOut(BaseModel):
    id: int
    name: str
    date_of_birth: str
    gender: str
    bio: Optional[str] = None
    intent: str
    city: str
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    phone_verified: bool
    photo_verified: bool
    profile_complete: bool
    is_premium: bool
    preferred_language: str
    show_online_status: bool
    last_active: Optional[datetime] = None
    photos: list[UserPhotoOut] = []
    languages: list[UserLanguageOut] = []
    voice_prompts: list[VoicePromptOut] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class UserSummaryOut(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    city: str
    intent: str
    photo_verified: bool
    model_config = {"from_attributes": True}


# ── Discovery ──

class DiscoveryProfileOut(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    city: str
    intent: str
    bio: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    college: Optional[str] = None
    workplace: Optional[str] = None
    photo_verified: bool
    distance_km: Optional[float] = None
    photos: list[UserPhotoOut] = []
    languages: list[UserLanguageOut] = []
    voice_prompts: list[VoicePromptOut] = []
    model_config = {"from_attributes": True}


# ── Swipes ──

class SwipeRequest(BaseModel):
    swiped_id: int
    direction: str


class SwipeStatsOut(BaseModel):
    likes_remaining: int
    super_likes_remaining: int


# ── Matches ──

class MatchOut(BaseModel):
    id: int
    matched_at: datetime
    is_active: bool
    user: UserSummaryOut
    model_config = {"from_attributes": True}


# ── Messages ──

class MessageOut(BaseModel):
    id: int
    match_id: int
    sender_id: int
    message_type: str
    content: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class MessageListItem(BaseModel):
    id: int
    match_id: int
    sender_id: int
    message_type: str
    content: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    message_type: str = "text"
    content: str


class WomenFirstStatus(BaseModel):
    can_send: bool
    reason: Optional[str] = None


# ── Family Share ──

class FamilyShareRequest(BaseModel):
    shared_with_email: Optional[str] = None
    shared_with_phone: Optional[str] = None


class FamilyShareOut(BaseModel):
    id: int
    profile_user_id: int
    share_url: str
    expires_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SharedProfileOut(BaseModel):
    name: str
    age: int
    city: str
    intent: str
    bio: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    photos: list[UserPhotoOut] = []
    voice_prompts: list[VoicePromptOut] = []


# ── Verification ──

class VerificationStatusOut(BaseModel):
    phone_verified: bool
    photo_verified: bool


# ── Preferences ──

class PreferencesOut(BaseModel):
    id: int
    min_age: int
    max_age: int
    preferred_gender: str
    max_distance_km: int
    intent_filter: Optional[str] = None
    city_filter: Optional[str] = None
    model_config = {"from_attributes": True}


class UpdatePreferencesRequest(BaseModel):
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    preferred_gender: Optional[str] = None
    max_distance_km: Optional[int] = None
    intent_filter: Optional[str] = None
    city_filter: Optional[str] = None


class UpdateNotificationSettingsRequest(BaseModel):
    show_online_status: Optional[bool] = None
    show_distance: Optional[bool] = None


# ── Notifications ──

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: Optional[str] = None
    is_read: bool
    related_user_id: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Reports & Blocks ──

class ReportRequest(BaseModel):
    reported_id: int
    reason: Optional[str] = None


class BlockedUserOut(BaseModel):
    id: int
    name: str
    blocked_at: datetime
    model_config = {"from_attributes": True}


# ── Subscriptions ──

class SubscriptionOut(BaseModel):
    id: int
    plan_type: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class SubscriptionOrderOut(BaseModel):
    order_id: str
    amount: int
    currency: str = "INR"


class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str


# ── Admin ──

class AdminDashboardOut(BaseModel):
    total_users: int
    active_users_today: int
    matches_today: int
    reports_pending: int
    premium_users: int = 0
    total_photos: int = 0
    total_swipes: int = 0
    total_messages: int = 0


class AdminReportOut(BaseModel):
    id: int
    reporter_id: int
    reported_id: int
    reporter_name: str = ""
    reported_name: str = ""
    reason: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminHandleReportRequest(BaseModel):
    action: str


class AdminUserOut(BaseModel):
    id: int
    name: str
    phone_number: str
    city: str
    gender: str = ""
    is_active: bool
    is_premium: bool
    phone_verified: bool = False
    photo_verified: bool = False
    profile_complete: bool = False
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminUserDetailOut(BaseModel):
    id: int
    name: str
    phone_number: str
    email: Optional[str] = None
    date_of_birth: str = ""
    gender: str = ""
    bio: Optional[str] = None
    intent: str = ""
    city: str = ""
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    phone_verified: bool = False
    photo_verified: bool = False
    profile_complete: bool = False
    is_premium: bool = False
    is_active: bool = True
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    preferred_language: str = "en"
    last_active: Optional[datetime] = None
    created_at: Optional[datetime] = None
    photos: list[UserPhotoOut] = []
    languages: list[UserLanguageOut] = []
    voice_prompts: list[VoicePromptOut] = []
    model_config = {"from_attributes": True}


class AdminPhotoOut(BaseModel):
    id: int
    user_id: int
    user_name: str = ""
    photo_url: str
    is_primary: bool = False
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class AdminVoicePromptOut(BaseModel):
    id: int
    user_id: int
    user_name: str = ""
    prompt_question: str
    audio_url: str
    duration_seconds: Optional[int] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class AdminSubscriptionOut(BaseModel):
    id: int
    user_id: int
    user_name: str = ""
    plan_type: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class AdminUserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None
    photo_verified: Optional[bool] = None


# ── Common ──

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
