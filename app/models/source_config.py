from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, Integer, Boolean, String, Enum as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
from app.domain.types import SourceType

class SourceConfig(Base):
    __tablename__ = "source_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_group_id: Mapped[int] = mapped_column(ForeignKey("source_groups.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[SourceType] = mapped_column(PgEnum(SourceType, name="source_type", create_constraint=False), nullable=False)
    brand_name: Mapped[str] = mapped_column(String(200), nullable=False)
    countries: Mapped[dict] = mapped_column(JSONB, default=list)
    number_of_reviews: Mapped[int] = mapped_column(Integer, default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    options: Mapped[dict] = mapped_column(JSONB, default=dict)

    # relationship
    source_group: Mapped["SourceGroup"] = relationship(back_populates="sources")
