from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Text, Enum as PgEnum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from app.db.base import Base
from app.domain.types import JobStatus, JobSourceStatus, SourceType, JobType, JobTargetType
from typing import Optional
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    
    # Job type and target information
    job_type: Mapped[JobType] = mapped_column(
        PgEnum(JobType, name="job_type", create_constraint=False), 
        default=JobType.REVIEW_SCRAPING, 
        nullable=False
    )
    target_type: Mapped[JobTargetType] = mapped_column(
        PgEnum(JobTargetType, name="job_target_type", create_constraint=False),
        default=JobTargetType.ORGANIZATION,
        nullable=False
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)  # organization_id or competitor_id
    
    status: Mapped[JobStatus] = mapped_column(PgEnum(JobStatus, name="job_status", create_constraint=False), default=JobStatus.PENDING, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)  # Store job results
    created_at: Mapped[datetime]
    started_at: Mapped[Optional[datetime]]
    finished_at: Mapped[Optional[datetime]]

    sources: Mapped[list["JobSource"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    events: Mapped[list["JobEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")

    discovered_products: Mapped[list["DiscoveredProduct"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    discovered_places: Mapped[list["DiscoveredPlaces"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    archetypes: Mapped[list["Archetype"]] = relationship(back_populates="job", cascade="all, delete-orphan")

class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[SourceType] = mapped_column(PgEnum(SourceType, name="source_type", create_constraint=False), nullable=False)
    status: Mapped[JobSourceStatus] = mapped_column(PgEnum(JobSourceStatus, name="job_source_status", create_constraint=False), default=JobSourceStatus.PENDING, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]

    job: Mapped["Job"] = relationship(back_populates="sources")

class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    at: Mapped[datetime]
    event: Mapped[str]
    data: Mapped[dict] = mapped_column(JSONB, default=dict)

    job: Mapped["Job"] = relationship(back_populates="events")
