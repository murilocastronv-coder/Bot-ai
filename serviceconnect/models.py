"""Modelos SQLAlchemy — todos os dados ficam permanentemente no PostgreSQL."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import (JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint, Index)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_ref_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128), default="")
    language: Mapped[str] = mapped_column(String(5), default="pt")
    city: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    is_provider: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime)
    announcements_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str | None] = mapped_column(String(255))
    blocked_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, default=new_ref_code)
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    plan_code: Mapped[str] = mapped_column(String(32), default="free")
    plan_until: Mapped[datetime | None] = mapped_column(DateTime)
    early_adopter: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    provider: Mapped["ProviderProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")

    def has_paid_plan(self) -> bool:
        return self.plan_code != "free" and (self.plan_until is None or self.plan_until > utcnow())


class ProviderProfile(Base):
    __tablename__ = "provider_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    business_name: Mapped[str] = mapped_column(String(128), default="")
    photo_file_id: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    category_ids: Mapped[list] = mapped_column(JSON, default=list)
    radius_km: Mapped[int] = mapped_column(Integer, default=25)
    price_type: Mapped[str] = mapped_column(String(16), default="quote")  # hourly | quote
    hourly_rate: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    availability: Mapped[str] = mapped_column(String(255), default="")
    notify_new_requests: Mapped[bool] = mapped_column(Boolean, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    jobs_done: Mapped[int] = mapped_column(Integer, default=0)
    profile_views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="provider", lazy="joined")
    photos: Mapped[list["PortfolioPhoto"]] = relationship(cascade="all, delete-orphan", order_by="PortfolioPhoto.id", lazy="selectin")


class PortfolioPhoto(Base):
    __tablename__ = "portfolio_photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(48), unique=True)
    emoji: Mapped[str] = mapped_column(String(8), default="✨")
    names: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=100)

    def label(self, lang: str) -> str:
        names = self.names or {}
        return f"{self.emoji} {names.get(lang) or names.get('en') or names.get('pt') or self.key}"


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    photo_file_ids: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    budget: Mapped[str | None] = mapped_column(String(64))
    desired_date: Mapped[str | None] = mapped_column(String(64))
    urgency: Mapped[str] = mapped_column(String(16), default="normal")  # low|normal|high|urgent
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)  # open|assigned|completed|cancelled|hidden
    assigned_provider_id: Mapped[int | None] = mapped_column(ForeignKey("provider_profiles.id", ondelete="SET NULL"))
    provider_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    client: Mapped[User] = relationship(foreign_keys=[client_id], lazy="joined")
    category: Mapped[Category] = relationship(lazy="joined")


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (UniqueConstraint("request_id", "provider_id", name="uq_proposal_once"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    price: Mapped[str] = mapped_column(String(64))
    availability: Mapped[str] = mapped_column(String(255), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|accepted|rejected|withdrawn
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    request: Mapped[ServiceRequest] = relationship(lazy="joined")
    provider: Mapped[ProviderProfile] = relationship(lazy="joined")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("client_id", "provider_user_id", "request_id", name="uq_conversation"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("service_requests.id", ondelete="SET NULL"))
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str | None] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String(255))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("request_id", "reviewer_id", name="uq_review_once"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Report(Base):
    """Denúncias e pedidos de suporte."""
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), default="report")  # report | support
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id", ondelete="SET NULL"))
    request_id: Mapped[int | None] = mapped_column(ForeignKey("service_requests.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | resolved | dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    price_eur: Mapped[float] = mapped_column(Float, default=0.0)
    price_stars: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_code: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(16), default="stars")  # stars | admin_grant | promo
    stars_amount: Mapped[int] = mapped_column(Integer, default=0)
    telegram_charge_id: Mapped[str | None] = mapped_column(String(255))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Promotion(Base):
    __tablename__ = "promotions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    plan_code: Mapped[str] = mapped_column(String(32))
    days: Mapped[int] = mapped_column(Integer, default=30)
    max_uses: Mapped[int] = mapped_column(Integer, default=100)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PromotionUse(Base):
    __tablename__ = "promotion_uses"
    __table_args__ = (UniqueConstraint("promotion_id", "user_id", name="uq_promo_use"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (Index("ix_city_name_country", "name", "country"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(8))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)


class Broadcast(Base):
    __tablename__ = "broadcasts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audience: Mapped[str] = mapped_column(String(16), default="all")
    text: Mapped[str] = mapped_column(Text)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FSMRecord(Base):
    """Estado das conversas do bot persistido no banco (sobrevive a reinícios do Render)."""
    __tablename__ = "fsm_states"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    state: Mapped[str | None] = mapped_column(String(128))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
