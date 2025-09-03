from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import Optional
from app.db.base import Base

class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    
    # Configuration for scraping/analysis
    source_configs: Mapped[dict] = mapped_column(JSONB, default=list)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[Optional[datetime]]
    
    # Relationships
    organization: Mapped["Organization"] = relationship()
    archetypes: Mapped[list["Archetype"]] = relationship(back_populates="competitor")