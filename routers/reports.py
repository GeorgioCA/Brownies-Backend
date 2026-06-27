from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_user
from core.exceptions import NotFoundException, ValidationException
from models import User, Match, BlockReport, Notification
from schemas import ReportRequest, BlockedUserOut, SuccessResponse

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}", tags=["reports"])


@router.post("/reports")
async def report_user(
    req: ReportRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.reported_id == user.id:
        raise ValidationException("Cannot report yourself")

    target = await db.execute(select(User).where(User.id == req.reported_id))
    if not target.scalar_one_or_none():
        raise NotFoundException("User not found")

    existing = await db.execute(
        select(BlockReport).where(
            BlockReport.reporter_id == user.id,
            BlockReport.reported_id == req.reported_id,
            BlockReport.type == "report",
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationException("Already reported this user")

    report = BlockReport(
        reporter_id=user.id,
        reported_id=req.reported_id,
        reason=req.reason,
        type="report",
    )
    db.add(report)
    return SuccessResponse(message="User reported")


@router.post("/blocks")
async def block_user(
    req: ReportRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.reported_id == user.id:
        raise ValidationException("Cannot block yourself")

    target = await db.execute(select(User).where(User.id == req.reported_id))
    if not target.scalar_one_or_none():
        raise NotFoundException("User not found")

    existing = await db.execute(
        select(BlockReport).where(
            BlockReport.reporter_id == user.id,
            BlockReport.reported_id == req.reported_id,
            BlockReport.type == "block",
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationException("Already blocked this user")

    block = BlockReport(
        reporter_id=user.id,
        reported_id=req.reported_id,
        reason=req.reason,
        type="block",
    )
    db.add(block)

    # Unmatch if matched
    u1, u2 = (user.id, req.reported_id) if user.id < req.reported_id else (req.reported_id, user.id)
    match_result = await db.execute(
        select(Match).where(
            Match.user1_id == u1, Match.user2_id == u2, Match.is_active == True
        )
    )
    m = match_result.scalar_one_or_none()
    if m:
        m.is_active = False
        m.unmatched_by = user.id

    return SuccessResponse(message="User blocked")


@router.delete("/blocks/{target_id}")
async def unblock_user(
    target_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BlockReport).where(
            BlockReport.reporter_id == user.id,
            BlockReport.reported_id == target_id,
            BlockReport.type == "block",
        )
    )
    block = result.scalar_one_or_none()
    if not block:
        raise NotFoundException("Block not found")
    await db.delete(block)
    return SuccessResponse(message="User unblocked")


@router.get("/blocks", response_model=list[BlockedUserOut])
async def get_blocked_users(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BlockReport).where(
            BlockReport.reporter_id == user.id,
            BlockReport.type == "block",
        ).order_by(BlockReport.created_at.desc())
    )
    blocks = result.scalars().all()
    out = []
    for b in blocks:
        target_result = await db.execute(select(User).where(User.id == b.reported_id))
        target = target_result.scalar_one_or_none()
        if target:
            out.append(BlockedUserOut(id=target.id, name=target.name, blocked_at=b.created_at))
    return out
