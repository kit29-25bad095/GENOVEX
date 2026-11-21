from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class PasswordResetToken(Base):
    """
    Persistent SQLAlchemy model for unauthenticated password reset tokens.
    Integrated directly into the primary application database schema (PostgreSQL & SQLite).
    Stores cryptographically secure SHA-256 token digests with UTC expiration,
    single-use consumption tracking, and foreign-key cascade deletion on user removal.
    Raw tokens are never persisted or logged.
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_consumed = Column(Boolean, default=False, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)

    user = relationship("User", back_populates="password_reset_tokens")

    __table_args__ = (
        Index("ix_password_reset_tokens_active_lookup", "token_hash", "is_consumed", "expires_at"),
    )

def get_token_db_session():
    """Compatibility alias returning a session to the primary database."""
    from app.core.database import SessionLocal
    return SessionLocal()

