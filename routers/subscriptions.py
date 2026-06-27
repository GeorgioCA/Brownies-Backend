from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.auth_deps import get_current_user
from ..core.exceptions import NotFoundException
from ..models import Subscription
from ..schemas import SubscriptionOut, SubscriptionOrderOut, VerifyPaymentRequest, SuccessResponse

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/subscriptions", tags=["subscriptions"])


PLANS = [
    {"id": "free", "name": "Free", "price": 0, "duration_days": 0},
    {"id": "premium_monthly", "name": "Premium Monthly", "price": 49900, "duration_days": 30},
    {"id": "premium_yearly", "name": "Premium Yearly", "price": 299900, "duration_days": 365},
]


@router.get("/plans")
async def get_plans():
    return {"plans": PLANS}


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
    plan_id: str = "premium_monthly",
    user=Depends(get_current_user),
):
    plan = next((p for p in PLANS if p["id"] == plan_id), None)
    if not plan or plan["price"] == 0:
        from ..core.exceptions import ValidationException
        raise ValidationException("Invalid plan")

    order_id = f"order_{user.id}_{datetime.now(timezone.utc).timestamp():.0f}"
    return SubscriptionOrderOut(order_id=order_id, amount=plan["price"])


@router.post("/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # In production: verify with Razorpay/Stripe
    plan_id = "premium_monthly"  # Extract from order in production
    duration = 30

    sub = Subscription(
        user_id=user.id,
        plan_type=plan_id,
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
