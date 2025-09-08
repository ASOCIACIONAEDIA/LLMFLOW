from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Text, DateTime, Boolean, String
from app.db.base import Base
from typing import Optional
import uuid

class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[str] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False) 
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    # relationships
    user: Mapped["User"] = relationship(back_populates="email_verifications")

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None
    
    def __repr__(self) -> str:
        return f"<EmailVerification(id={self.id}, user_id={self.user_id}, verified_at={self.verified_at})>"