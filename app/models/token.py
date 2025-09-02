from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from datetime import datetime

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]

    # relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")