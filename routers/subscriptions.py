from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.auth_deps import get_current_user
from core.exceptions import NotFoundException
from models import Subscription, Plan
from schemas import SubscriptionOut, SubscriptionOrderOut, VerifyPaymentRequest, SuccessResponse

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/subscriptions", tags=["subscriptions"])


async def _get_plans(db: AsyncSession):
    result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.sort_order))
    return result.scalars().all()


@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    plans = await _get_plans(db)
    return {
        "plans": [
            {"id": str(p.id), "name": p.name, "price": p.price_paise, "duration_days": p.duration_days}
            for p in plans
        ]
    }


@router.get("/me", response_model=SubscriptionOut)
async def get_my_subscription(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.is_active == True
        ).order_by(Subscription.ends_at.desc())
    )
    sub = result.scalars().first()
    if not sub:
        return SubscriptionOut(id=0, plan_type="free", starts_at=user.created_at, ends_at=datetime(2099, 1, 1), is_active=True)
    return SubscriptionOut.model_validate(sub)


@router.post("/order", response_model=SubscriptionOrderOut)
async def create_order(
    plan_id: int = Query(..., description="Database plan ID"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.is_active == True))
    plan = result.scalar_one_or_none()
    if not plan or plan.price_paise == 0:
        from core.exceptions import ValidationException
        raise ValidationException("Invalid plan")

    order_id = f"order_{user.id}_{datetime.now(timezone.utc).timestamp():.0f}"
    return SubscriptionOrderOut(order_id=order_id, amount=plan.price_paise)


@router.post("/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    duration = 30
    plan_name = "premium_monthly"

    if req.plan_id:
        plan_result = await db.execute(select(Plan).where(Plan.id == req.plan_id))
        plan = plan_result.scalar_one_or_none()
        if plan:
            duration = plan.duration_days
            plan_name = plan.name

    sub = Subscription(
        user_id=user.id,
        plan_type=plan_name,
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(days=duration),
        is_active=True,
    )
    db.add(sub)

    # Deactivate old subs
    old_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.id != sub.id
        )
    )
    for old in old_result.scalars().all():
        old.is_active = False

    user.is_premium = True
    await db.flush()
    return SuccessResponse(message="Payment verified, premium activated")


@router.post("/cancel")
async def cancel_subscription(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.is_active == True
        )
    )
    for sub in result.scalars().all():
        sub.is_active = False
    user.is_premium = False
    return SuccessResponse(message="Subscription cancelled")
