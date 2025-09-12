from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, String, Text, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import Optional
from app.db.base import Base

class DiscoveredPlaces(Base):
    __tablename__ = "discovered_places"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    google_place_id: Mapped[str] = mapped_column(String(255), nullable=False)
    full_address: Mapped[str] = mapped_column(Text, nullable=False)
    postal_code: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(255), nullable=False)
    typical_time_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    num_reviews: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    # relationships
    job: Mapped["Job"] = relationship(back_populates="discovered_places")
    reviews: Mapped[list["Review"]] = relationship(back_populates="discovered_place")
