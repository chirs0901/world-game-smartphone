"""Game session and turn ORM models."""

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class GameSessionModel(TimestampMixin, Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    current_turn: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_year: Mapped[int] = mapped_column(Integer, nullable=False, default=2025)
    current_quarter: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class TurnModel(TimestampMixin, Base):
    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id: Mapped[str] = mapped_column(String(36), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
