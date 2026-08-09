"""Identity, role and authentication persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from momo_fdvs.extensions import Base
from momo_fdvs.models.base import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from momo_fdvs.models.evidence import Transaction


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'DISABLED', 'PENDING')", name="status_valid"),
        CheckConstraint("token_version >= 1", name="token_version_positive"),
        Index("ix_users_status", "status"),
    )

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    must_change_password: Mapped[bool] = mapped_column(nullable=False, default=False)

    role_grants: Mapped[list[UserRole]] = relationship(
        foreign_keys="UserRole.user_id", back_populates="user"
    )
    transactions: Mapped[list[Transaction]] = relationship(back_populates="user")


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint("code IN ('USER', 'ADMIN', 'INVESTIGATOR')", name="code_valid"),
    )

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    role_code: Mapped[str] = mapped_column(
        String(30), ForeignKey("roles.code", ondelete="RESTRICT"), primary_key=True
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="role_grants")
    role: Mapped[Role] = relationship()
    grantor: Mapped[User | None] = relationship(foreign_keys=[granted_by])


class AdminProfile(Base):
    __tablename__ = "admin_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    staff_reference: Mapped[str | None] = mapped_column(String(100), unique=True)
    department: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship()


class RefreshSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = (
        CheckConstraint("char_length(token_hash) = 64", name="token_hash_length"),
        CheckConstraint(
            "user_agent_hash IS NULL OR char_length(user_agent_hash) = 64",
            name="user_agent_hash_length",
        ),
        CheckConstraint("ip_hash IS NULL OR char_length(ip_hash) = 64", name="ip_hash_length"),
        Index("ix_refresh_sessions_user_id", "user_id"),
        Index("ix_refresh_sessions_family_id", "family_id"),
        Index("ix_refresh_sessions_expires_at", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(50))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("refresh_sessions.id", ondelete="RESTRICT")
    )
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))
    ip_hash: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship()
    replaced_by: Mapped[RefreshSession | None] = relationship(remote_side="RefreshSession.id")


class PasswordResetToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        CheckConstraint("char_length(token_hash) = 64", name="token_hash_length"),
        CheckConstraint(
            "requested_ip_hash IS NULL OR char_length(requested_ip_hash) = 64",
            name="requested_ip_hash_length",
        ),
        Index("ix_password_reset_tokens_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_ip_hash: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship()
