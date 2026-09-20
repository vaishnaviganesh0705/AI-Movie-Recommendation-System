from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.sql import func
from app.database import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10,2), nullable=False)
    duration_days = Column(Integer, default=30)
    features = Column(String(500), nullable=True)

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(String(50), default="active")
    started_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=True)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False)
    amount = Column(Numeric(10,2), nullable=False)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, server_default=func.now())
