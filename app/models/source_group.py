from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, ForeignKey, String, CheckConstraint
from app.db.base import Base
from typing import Optional
class SourceGroup(Base):
    __tablename__ = "source_groups"
    __table_args__ = (
        CheckConstraint("num_nonnulls(user_id, competitor_id) = 1", name="chk_source_group_owner"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    competitor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitors.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # relationships
    user: Mapped["User | None"] = relationship(back_populates="source_groups")
    competitor: Mapped["Competitor | None"] = relationship(back_populates="source_groups")

    sources: Mapped[list["SourceConfig"]] = relationship(back_populates="source_group", cascade="all, delete-orphan")