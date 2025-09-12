from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Text, String, DateTime, Float, Integer
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import Optional
from app.db.base import Base

class DiscoveredProduct(Base):
    __tablename__ = "discovered_products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    asin: Mapped[Optional[str]] = mapped_column(Text)
    amazon_url: Mapped[Optional[str]] = mapped_column(Text)
    druni_url: Mapped[Optional[str]] = mapped_column(Text)
    identifiers: Mapped[list] = mapped_column(JSONB, default=list)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    num_reviews: Mapped[int] = mapped_column(Integer, nullable=False)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # relationships
    job: Mapped["Job"] = relationship(back_populates="discovered_products")
    reviews: Mapped[list["Review"]] = relationship(back_populates="discovered_product")
