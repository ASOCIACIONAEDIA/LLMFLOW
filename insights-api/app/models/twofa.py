from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Text, DateTime
from app.db.base import Base
from datetime import datetime, timezone
from typing import Optional

class TwoFactorCode(Base):
    __tablename__ = "two_factor_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # FIXED: Add timezone=True
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # FIXED: Add timezone=True
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    user: Mapped["User"] = relationship(back_populates="twofa_codes")