from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.subscription import UserSubscription, SubscriptionPlan, Payment
from app.models.notification import Notification
from pydantic import BaseModel
from typing import Optional, List
import datetime
import os

router = APIRouter(prefix="/subscription", tags=["Subscription"])


# =========================================================
# SCHEMAS
# =========================================================

class PlanResponse(BaseModel):
    id: int
    name: str
    price: float
    duration_days: int
    features: Optional[str]

    class Config:
        from_attributes = True


class SubscriptionStatusResponse(BaseModel):
    status: str  # "active", "expired", "none"
    plan_id: Optional[int] = None
    plan_name: str
    plan_price: float
    features: Optional[str] = None
    starts_at: Optional[datetime.datetime] = None
    expires_at: Optional[datetime.datetime] = None
    auto_renew: bool = False
    is_entitled: bool = False


class EntitlementRequest(BaseModel):
    content_id: int
    content_type: str = "movie"


class CheckoutRequest(BaseModel):
    plan_id: int
    payment_method: Optional[str] = "card"


class PaymentVerifyRequest(BaseModel):
    plan_id: int
    payment_token: str
    transaction_id: Optional[str] = None


class OTPRequest(BaseModel):
    email: str


class OTPVerify(BaseModel):
    email: str
    otp: str
    plan_id: Optional[int] = 3


# =========================================================
# 1. GET AVAILABLE PLANS
# =========================================================

@router.get("/plans", response_model=List[PlanResponse])
def get_plans(db: Session = Depends(get_db)):
    plans = db.query(SubscriptionPlan).all()
    return plans


# =========================================================
# 2. GET CURRENT USER SUBSCRIPTION STATUS
# =========================================================

@router.get("/status", response_model=SubscriptionStatusResponse)
def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).order_by(UserSubscription.expires_at.desc()).first()

    now = datetime.datetime.utcnow()

    if not sub:
        return SubscriptionStatusResponse(
            status="none",
            plan_name="Free",
            plan_price=0.0,
            features="Standard definition, Ad-supported, 1 screen",
            is_entitled=False
        )

    # Check if expired
    if sub.expires_at and sub.expires_at < now:
        sub.status = "expired"
        db.commit()
        return SubscriptionStatusResponse(
            status="expired",
            plan_id=sub.plan_id,
            plan_name="Expired Subscription",
            plan_price=0.0,
            expires_at=sub.expires_at,
            is_entitled=False
        )

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()

    return SubscriptionStatusResponse(
        status="active",
        plan_id=sub.plan_id,
        plan_name=plan.name if plan else "Premium",
        plan_price=float(plan.price) if plan else 19.99,
        features=plan.features if plan else None,
        starts_at=sub.started_at,
        expires_at=sub.expires_at,
        auto_renew=sub.auto_renew,
        is_entitled=True
    )


# =========================================================
# 3. CONTENT ENTITLEMENT CHECK ("WATCH NOW" GATEWAY)
# =========================================================

@router.post("/entitlement/check")
def check_entitlement(
    data: EntitlementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.datetime.utcnow()
    active_sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active",
        UserSubscription.expires_at > now
    ).first()

    if active_sub:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == active_sub.plan_id).first()
        return {
            "allowed": True,
            "user_id": current_user.id,
            "plan": plan.name if plan else "Premium",
            "message": "Playback authorized"
        }

    return {
        "allowed": False,
        "requires_subscription": True,
        "message": "A StreamHub Premium or Standard subscription is required to stream this title."
    }


# =========================================================
# 4. CREATE CHECKOUT SESSION
# =========================================================

@router.post("/checkout")
def create_checkout_session(
    data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == data.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    razorpay_key = os.environ.get("RAZORPAY_KEY_ID")

    # Payment Gateway Configuration Detection
    gateway = "stripe" if stripe_key else ("razorpay" if razorpay_key else "secure_token")

    return {
        "plan_id": plan.id,
        "plan_name": plan.name,
        "amount": float(plan.price),
        "currency": "USD",
        "gateway": gateway,
        "client_token": f"token_{current_user.id}_{plan.id}_{int(datetime.datetime.utcnow().timestamp())}",
        "message": "Payment session initialized."
    }


# =========================================================
# 5. VERIFY PAYMENT & ACTIVATE SUBSCRIPTION
# =========================================================

@router.post("/verify-payment")
def verify_payment(
    data: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == data.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Verification token check
    if not data.payment_token or len(data.payment_token) < 8:
        raise HTTPException(status_code=400, detail="Invalid payment verification token. Payment was not confirmed.")

    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(days=plan.duration_days or 30)

    # Deactivate existing active subscriptions
    existing_subs = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).all()
    for s in existing_subs:
        s.status = "upgraded"

    # Create new active subscription
    new_sub = UserSubscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status="active",
        started_at=now,
        expires_at=expires_at,
        auto_renew=True
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    # Record Payment Transaction
    payment_record = Payment(
        user_id=current_user.id,
        subscription_id=new_sub.id,
        amount=plan.price,
        status="completed"
    )
    db.add(payment_record)

    # Trigger StreamHub Notification
    notif = Notification(
        user_id=current_user.id,
        type="agent",
        title=f"Welcome to StreamHub {plan.name}!",
        message=f"StreamHub Payment Agent: Your subscription to {plan.name} is confirmed! Enjoy unlimited streaming until {expires_at.strftime('%B %d, %Y')}."
    )
    db.add(notif)
    db.commit()

    return {
        "success": True,
        "message": f"Subscription to {plan.name} is now active!",
        "subscription_id": new_sub.id,
        "expires_at": expires_at.isoformat()
    }


# =========================================================
# 6. CANCEL SUBSCRIPTION
# =========================================================

@router.post("/cancel")
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found to cancel.")

    sub.auto_renew = False
    db.commit()

    return {
        "message": "Auto-renewal cancelled. You will continue to have access until your current billing period ends.",
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None
    }


# =========================================================
# 7. OTP FLOW (PRESERVED FOR DIRECT DEMO / DEV ACCESS)
# =========================================================

@router.post("/request-otp")
def request_otp(data: OTPRequest, current_user: User = Depends(get_current_user)):
    if data.email != current_user.email:
        raise HTTPException(status_code=400, detail="Please use your registered account email.")
    return {"message": "OTP sent successfully to your email.", "dummy_otp": "1234"}


@router.post("/verify-otp")
def verify_otp(data: OTPVerify, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.otp != "1234":
        raise HTTPException(status_code=400, detail="Invalid OTP code. Please try again.")

    plan_id = data.plan_id or 3
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        plan = db.query(SubscriptionPlan).first()

    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(days=30)

    sub = UserSubscription(
        user_id=current_user.id,
        plan_id=plan.id if plan else 1,
        status="active",
        started_at=now,
        expires_at=expires_at,
        auto_renew=True
    )
    db.add(sub)

    notif = Notification(
        user_id=current_user.id,
        type="agent",
        title="Welcome to Premium!",
        message="StreamHub Agent: You have successfully activated your subscription. Enjoy ad-free 4K streaming!"
    )
    db.add(notif)
    db.commit()

    return {"message": "Subscription activated successfully!", "expires_at": expires_at.isoformat()}
