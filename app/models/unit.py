from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Text, ForeignKey
from app.db.base import Base
from typing import Optional
class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # relationship
    organization: Mapped["Organization"] = relationship(back_populates="units")
    users: Mapped[list["User"]] = relationship(back_populates="unit")
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="unit", cascade="all, delete-orphan")