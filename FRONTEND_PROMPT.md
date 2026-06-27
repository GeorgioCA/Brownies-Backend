# Frontend Build Prompt — Brownies Dating App

You are building a **mobile-first dating app frontend** for the Brownies backend. Treat this as the full spec.

---

## Tech Stack (your choice)
Use **React Native** (Expo) or **Flutter** — whichever you produce faster, high-quality code with. Tailwind or native styling, up to you.

---

## Backend Base URL
```
http://<host>:8000/api/v1
```
The backend has CORS open (`*`), so no CORS issues.

---

## Authentication Flow

### 1. Send OTP
```
POST /auth/send-otp
Body: { "phone_number": "+919876543210" }
Response: { "success": true, "otp": "123456", "expires_in_seconds": 300 }
```
Show a phone input screen. In dev, the OTP is returned in the response; show it to the user.

### 2. Verify OTP
```
POST /auth/verify-otp
Body: { "phone_number": "...", "otp": "123456" }
Response: {
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "profile_complete": false | true
}
```
- If `profile_complete` is `false` → navigate to profile setup.
- If `true` → navigate to main app.

### 3. Set Password (first-time users)
```
POST /auth/set-password
Headers: Authorization: Bearer <access_token>
Body: { "password": "min 6 chars" }
```

### 4. Login (returning users)
```
POST /auth/login
Body: { "phone_number": "...", "password": "..." }
Response: { "access_token": "...", "refresh_token": "..." }
```

### 5. Refresh Token
```
POST /auth/refresh
Body: { "refresh_token": "..." }
Response: { "access_token": "...", "refresh_token": "..." }
```

### 6. Logout / Delete Account
```
POST /auth/logout          (no body, just clears server-side refresh token)
DELETE /auth/account        (deletes user + all data)
```
All authenticated requests: header `Authorization: Bearer <access_token>`

---

## Profile Setup & Management

### Setup (after first OTP)
```
POST /profile/setup
Body: {
  "name": "string (2-50)",
  "date_of_birth": "YYYY-MM-DD",
  "gender": "male" | "female",
  "intent": "lets_see" | "serious_relationship" | "casual" | "friendship" | "marriage",
  "city": "string",
  "bio": "string (optional)",
  "college": "string (optional)",
  "workplace": "string (optional)",
  "height_cm": 170 (optional),
  "religion": "string (optional)",
  "education": "string (optional)",
  "occupation": "string (optional)",
  "languages": ["en", "hi"],
  "preferred_language": "en"
}
Response: full UserProfileOut (see schemas below)
```

Create a multi-step onboarding UI (name + DOB → gender + intent → city → optional fields → photo upload).

### Get My Profile
```
GET /profile/me → UserProfileOut
```
### Update Profile
```
PATCH /profile/me
Body: { "name", "bio", "intent", "city", "college", "workplace", "height_cm", "religion", "education", "occupation", "preferred_language", "location_lat", "location_lng" }
(all fields optional)
```

### Photos
```
POST   /profile/photos            multipart/form-data, field name: "file"
GET    (photos come embedded in UserProfileOut)
DELETE /profile/photos/{photo_id}
PUT    /profile/photos/reorder    Body: { "photo_ids": [3, 1, 2] }
```
Max 6 photos, upload via multipart. First uploaded becomes primary.

### Voice Prompts
```
GET    /profile/voice-prompts       → list[VoicePromptOut]
POST   /profile/voice-prompts       multipart: "file" + "prompt_question" + "duration_seconds"
DELETE /profile/voice-prompts/{id}
```
Max 60 seconds each.

### Languages
```
PUT /profile/languages    Body: { "languages": ["en", "hi"] }
```

### View Other User's Profile
```
GET /profile/{user_id} → UserProfileOut
```

---

## Discovery / Swiping

### Get Card Stack
```
GET /discovery?page=1&per_page=20
Response: list[DiscoveryProfileOut]
```
- Returns users matching the current user's preferences (age, gender, distance, etc.)
- Each profile includes photos, languages, voice prompts, distance_km
- Infinite scroll / paginated

### Swipe
```
POST /discovery/swipes
Body: { "swiped_id": 123, "direction": "like" | "super_like" | "pass" }
```
- When two users like each other → a Match is created (backend handles this).
- The swipe response includes `is_match: true/false` and `match_id` if matched.

### Undo Swipe
```
POST /discovery/swipes/undo
```
### Swipe Stats
```
GET /discovery/swipes/stats
Response: { "likes_remaining": 50, "super_likes_remaining": 1 }
```
- Free users: 50 likes/day, 1 super like/day

---

## Matches

### List My Matches
```
GET /matches → list[MatchOut]
```
Each match includes the other user's summary (name, age, gender, city, photo_verified).

### Get Single Match
```
GET /matches/{match_id} → MatchOut
```

### Unmatch
```
DELETE /matches/{match_id}
```

---

## Chat / Messages

### Get Messages for a Match
```
GET /matches/{match_id}/messages?page=1&per_page=50
Response: list[MessageListItem]
```
- Returns paginated messages in **chronological order** (oldest first).
- The response is already reversed by the backend.

### Send Message
```
POST /matches/{match_id}/messages
Body: { "message_type": "text", "content": "Hey!" }
Response: MessageOut
```
**Important rule:** There is a "women-first" feature. Check this before allowing send:
```
GET /matches/{match_id}/women-first-status
Response: { "can_send": true | false, "reason": "..." }
```

### Mark Messages as Read
```
PUT /matches/{match_id}/messages/read
```
Marks all unread messages from the other user as read.

---

## Real-Time WebSocket

Connect to `ws://<host>:8000/api/v1/ws`

### Auth (first message after connect)
```json
{ "token": "<access_token>" }
```

### Ping/Pong
```json
Send: { "type": "ping" }
Receive: { "type": "pong" }
```

### Typing Indicators
```json
Send: { "type": "typing_start", "data": { "match_id": 1 } }
Send: { "type": "typing_stop", "data": { "match_id": 1 } }
```

### Real-time Events (pushed by server)
The backend can push events like new match, new message — check `websocket/handler.py` for the `notify_user` function. Events come as:
```json
{ "type": "new_message" | "new_match" | "...", "data": { ... } }
```

---

## Notifications

```
GET /notifications                  → list[NotificationOut]
GET /notifications/unread-count     → { "count": 5 }
PUT /notifications/{id}/read        mark single as read
PUT /notifications/read-all         mark all as read
POST /notifications/push-token      Body: { "token": "fcm_token" }
```

---

## Preferences

```
GET  /preferences                  → PreferencesOut
PUT  /preferences                  → PreferencesOut
Body: { "min_age", "max_age", "preferred_gender", "max_distance_km", "intent_filter", "city_filter" }
(all fields optional)

PUT  /preferences/notification-settings
Body: { "show_online_status": true, "show_distance": true }
```

---

## Reports & Blocks

```
POST   /reports/reports  Body: { "reported_id": 5, "reason": "Inappropriate" }
POST   /reports/blocks   Body: { "blocked_id": 5 }
DELETE /reports/blocks/{target_id}
GET    /reports/blocks    → list[BlockedUserOut]
```

---

## Verification

```
GET  /verification/status
POST /verification/phone/send-otp   (re-verify phone)
POST /verification/phone/verify
POST /verification/photo            multipart: "file" (selfie for photo verification)
```

---

## Subscriptions / Premium

```
GET  /subscriptions/plans            hardcoded plan list
GET  /subscriptions/me               → SubscriptionOut
POST /subscriptions/order            creates Razorpay order
POST /subscriptions/verify           verifies payment signature
POST /subscriptions/cancel
```
Premium unlocks: unlimited likes, see who liked you, advanced filters.

---

## Family Share

```
POST   /family-share/{match_id}          → FamilyShareOut (share a match profile)
GET    /shared/{token}                   → SharedProfileOut (public, no auth)
DELETE /family-share/{share_id}
```

---

## Key Response Schemas

### UserProfileOut
```json
{
  "id": 1, "name": "Rahul", "date_of_birth": "1998-05-15",
  "gender": "male", "bio": "...", "intent": "serious_relationship",
  "city": "Mumbai", "college": null, "workplace": null,
  "height_cm": 175, "religion": null, "education": null, "occupation": null,
  "phone_verified": true, "photo_verified": false,
  "profile_complete": true, "is_premium": false,
  "preferred_language": "en", "show_online_status": true,
  "last_active": "2026-06-27T10:00:00Z",
  "photos": [{ "id": 1, "photo_url": "/api/v1/uploads/photos/...", "is_primary": true, "sort_order": 0 }],
  "languages": [{ "language": "en" }, { "language": "hi" }],
  "voice_prompts": [{ "id": 1, "prompt_question": "My favorite hobby...", "audio_url": "...", "duration_seconds": 15 }],
  "created_at": "2026-06-01T00:00:00Z"
}
```

### DiscoveryProfileOut
Same shape as UserProfileOut minus private fields (no phone, email): includes name, age, gender, city, intent, bio, photos, languages, voice_prompts, distance_km, photo_verified.

### MessageListItem / MessageOut
```json
{ "id": 1, "match_id": 5, "sender_id": 2, "message_type": "text",
  "content": "Hey!", "is_read": false, "created_at": "..." }
```

### MatchOut
```json
{ "id": 5, "matched_at": "...", "is_active": true,
  "user": { "id": 2, "name": "Priya", "age": 24, "gender": "female", "city": "Mumbai", "intent": "...", "photo_verified": true } }
```

---

## UI/UX Guidelines

### Screens needed:
1. **Splash** (logo)
2. **Phone Input** → **OTP Verify** → **Set Password** (first time) / **Login** (returning)
3. **Profile Setup** (multi-step: name+DOB, gender+intent, city, bio+optional fields, photo upload)
4. **Discovery** (Tinder-style card stack, swipe left/right, tap for profile detail)
5. **Match Screen** (match animation when both like each other)
6. **Chat List** (list of matches / conversations)
7. **Chat Detail** (message thread, text input, typing indicator via WebSocket)
8. **Profile** (my profile, edit, photos, voice prompts, verification status)
9. **Settings** (preferences, notification settings, logout, delete account)
10. **Premium/Subscription** (plan cards, Razorpay payment flow)

### Navigation:
Bottom tab bar: **Discover** | **Chats** | **Profile**

### Visual style:
- Warm, modern, "coffee/dessert" theme — browns, creams, gold accents
- Rounded cards with soft shadows
- Clean typography (Inter font)
- The existing admin dashboard at `/admin` uses this style — reference it for design tokens

---

## Running the Backend

```bash
# With Docker
docker compose up -d

# Without Docker
pip install -r requirements.txt
# Set DATABASE_URL env var to a running PostgreSQL
python main.py
```

Seed data:
```bash
python seed.py              # creates admin account (0000000000 / admin123)
python generate_dummy_data.py  # creates 20 users with matches + messages
```

Admin dashboard at `http://<host>:8000/admin` (login with admin account).

---

## Important Rules to Implement
- **Women-first messaging**: When a match is created, check `women-first-status` before letting the male user send the first message
- **Daily limits**: Show remaining likes from `swipes/stats`, disable swipe when at 0
- **Photo verification**: Users can upload a selfie for verification; badge shown on profile
- **Age from DOB**: The backend sends DOB as string, compute age client-side for display
- **Distance**: Shown in DiscoveryProfileOut when location available
- **Family Share**: Public profile sharing link (no auth required for viewing)

---

Build the complete app with all screens, navigation, state management, API integration, WebSocket, error handling, and loading states. Make it production-quality.
