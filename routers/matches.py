from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_user
from core.exceptions import NotFoundException, ForbiddenException, ValidationException
from models import User, Match, Message
from schemas import (
    MatchOut, UserSummaryOut,
    MessageListItem, MessageOut,
    SendMessageRequest, WomenFirstStatus,
    SuccessResponse,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/matches", tags=["matches"])


def _to_summary(other: User) -> UserSummaryOut:
    dob = other.date_of_birth
    age = 0
    if dob:
        try:
            d = datetime.strptime(dob, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except (ValueError, TypeError):
            pass
    return UserSummaryOut(
        id=other.id,
        name=other.name,
        age=age,
        gender=other.gender,
        city=other.city,
        intent=other.intent,
        photo_verified=other.photo_verified,
    )


@router.get("", response_model=list[MatchOut])
async def get_matches(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Match)
        .where(
            or_(Match.user1_id == user.id, Match.user2_id == user.id),
            Match.is_active == True,
        )
        .order_by(Match.matched_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    matches = result.scalars().all()

    out = []
    for m in matches:
        other_id = m.user2_id if m.user1_id == user.id else m.user1_id
        other_result = await db.execute(select(User).where(User.id == other_id))
        other = other_result.scalar_one_or_none()
        if other:
            out.append(MatchOut(
                id=m.id,
                matched_at=m.matched_at,
                is_active=m.is_active,
                user=_to_summary(other),
            ))
    return out


@router.get("/{match_id}", response_model=MatchOut)
async def get_match_detail(
    match_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise NotFoundException("Match not found")
    if user.id not in (match.user1_id, match.user2_id):
        raise ForbiddenException("Not your match")

    other_id = match.user2_id if match.user1_id == user.id else match.user1_id
    other_result = await db.execute(select(User).where(User.id == other_id))
    other = other_result.scalar_one_or_none()
    return MatchOut(
        id=match.id, matched_at=match.matched_at,
        is_active=match.is_active, user=_to_summary(other),
    )


@router.delete("/{match_id}")
async def unmatch(
    match_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise NotFoundException("Match not found")
    if user.id not in (match.user1_id, match.user2_id):
        raise ForbiddenException("Not your match")

    match.is_active = False
    match.unmatched_by = user.id
    return SuccessResponse(message="Unmatched")


# ── Messages ──

@router.get("/{match_id}/messages", response_model=list[MessageListItem])
async def get_messages(
    match_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match or user.id not in (match.user1_id, match.user2_id):
        raise ForbiddenException("Not your match")

    stmt = (
        select(Message)
        .where(Message.match_id == match_id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    msg_result = await db.execute(stmt)
    messages = msg_result.scalars().all()

    # Mark messages as read
    other_id = match.user2_id if match.user1_id == user.id else match.user1_id
    for msg in messages:
        if msg.sender_id == other_id and not msg.is_read:
            msg.is_read = True

    return [MessageListItem.model_validate(m) for m in reversed(messages)]


@router.post("/{match_id}/messages", response_model=MessageOut)
async def send_message(
    match_id: int,
    req: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match or user.id not in (match.user1_id, match.user2_id):
        raise ForbiddenException("Not your match")
    if not match.is_active:
        raise ValidationException("Match is no longer active")

    other_id = match.user2_id if match.user1_id == user.id else match.user1_id

    # Women-message-first check
    existing_msgs = await db.execute(
        select(Message).where(Message.match_id == match_id)
    )
    all_msgs = existing_msgs.scalars().all()
    first_msg_sent = len(all_msgs) > 0

    other_result = await db.execute(select(User).where(User.id == other_id))
    other = other_result.scalar_one_or_none()

    if not first_msg_sent and user.gender == "male" and (other and other.gender == "female"):
        raise ForbiddenException("Women must send the first message in this match")

    msg = Message(
        match_id=match_id,
        sender_id=user.id,
        message_type=req.message_type,
        content=req.content,
        is_read=False,
    )
    db.add(msg)
    await db.flush()
    return MessageOut.model_validate(msg)


@router.get("/{match_id}/women-first-status", response_model=WomenFirstStatus)
async def get_women_first_status(
    match_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match or user.id not in (match.user1_id, match.user2_id):
        raise ForbiddenException("Not your match")

    existing = await db.execute(select(Message).where(Message.match_id == match_id))
    if existing.scalars().all():
        return WomenFirstStatus(can_send=True)

    other_id = match.user2_id if match.user1_id == user.id else match.user1_id
    other_result = await db.execute(select(User).where(User.id == other_id))
    other = other_result.scalar_one_or_none()

    if user.gender == "male" and other and other.gender == "female":
        return WomenFirstStatus(can_send=False, reason="Women must send the first message")

    return WomenFirstStatus(can_send=True)


@router.put("/{match_id}/messages/read")
async def mark_messages_read(
    match_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match or user.id not in (match.user1_id, match.user2_id):
        raise ForbiddenException("Not your match")

    other_id = match.user2_id if match.user1_id == user.id else match.user1_id
    msgs = await db.execute(
        select(Message).where(
            Message.match_id == match_id,
            Message.sender_id == other_id,
            Message.is_read == False,
        )
    )
    for msg in msgs.scalars().all():
        msg.is_read = True

    return SuccessResponse(message="Messages marked as read")
