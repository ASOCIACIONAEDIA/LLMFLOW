from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Text, Integer, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.db.base import Base

class Archetype(Base):
    __tablename__ = "archetypes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    competitor_id: Mapped[int | None] = mapped_column(ForeignKey("competitors.id", ondelete="CASCADE"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    
    # Archetype data
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text)
    
    # Structured archetype fields (stored as JSON arrays/objects)
    pain_points: Mapped[list] = mapped_column(JSONB, default=list)
    fears_and_concerns: Mapped[dict] = mapped_column(JSONB, default=list)
    objections: Mapped[dict] = mapped_column(JSONB, default=list)
    goals_and_objectives: Mapped[dict] = mapped_column(JSONB, default=list)
    expected_benefits: Mapped[dict] = mapped_column(JSONB, default=list)
    values: Mapped[dict] = mapped_column(JSONB, default=list)
    influence_factors: Mapped[dict] = mapped_column(JSONB, default=list)
    
    # Text fields
    social_behavior: Mapped[str] = mapped_column(Text)
    internal_narrative: Mapped[str] = mapped_column(Text)
    
    # Metadata
    avatar_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]
    
    # Relationships
    job: Mapped["Job"] = relationship(back_populates="archetypes")
    competitor: Mapped["Competitor"] = relationship()