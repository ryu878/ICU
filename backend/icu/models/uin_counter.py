from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from icu.db.base import Base


class UinCounter(Base):
    """Single-row counter for gapless UIN (variant B). Row id must stay 1."""

    __tablename__ = "uin_counter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
