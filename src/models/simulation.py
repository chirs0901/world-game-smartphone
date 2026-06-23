"""Simulation (decision and result) ORM models."""

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class DecisionRecordModel(TimestampMixin, Base):
    __tablename__ = "decision_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id: Mapped[str] = mapped_column(String(36), nullable=False)
    turn: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_committed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
