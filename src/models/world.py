"""World snapshot ORM model."""

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class WorldSnapshotModel(TimestampMixin, Base):
    __tablename__ = "world_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id: Mapped[str] = mapped_column(String(36), nullable=False)
    turn: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    delta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
