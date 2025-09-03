from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Integer, Text, DateTime, Enum as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.db.base import Base
from app.domain.types import SourceType

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    discovered_product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("discovered_products.id", ondelete="SET NULL"))
    discovered_place_id: Mapped[Optional[int]] = mapped_column(ForeignKey("discovered_places.id", ondelete="SET NULL"))
    source: Mapped[SourceType] = mapped_column(PgEnum(SourceType, name="source_type", create_constraint=False), nullable=False)
    external_id: Mapped[str | None] = mapped_column(Text)
    brand_name: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    review_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime]

    # relationships
    discovered_product: Mapped["DiscoveredProduct | None"] = relationship(back_populates="reviews")
    discovered_place: Mapped["DiscoveredPlaces | None"] = relationship(back_populates="reviews")
    job: Mapped["Job"] = relationship(back_populates="reviews")