"""OKR (Objectives and Key Results) Pydantic schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class KRStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    MISSED = "missed"


class KeyResult(BaseModel):
    id: str = ""
    title: str
    metric: str
    target_value: float
    current_value: float = 0.0
    unit: str = ""
    status: KRStatus = KRStatus.NOT_STARTED
    progress: float = Field(0.0, ge=0.0, le=1.0)


class KeyResultHistory(BaseModel):
    turn_id: str
    value: float
    timestamp: str


class Objective(BaseModel):
    id: str = ""
    game_id: str = ""
    turn_created: int = 1
    title: str
    description: str = ""
    key_results: list[KeyResult] = []
    priority: int = Field(1, ge=1, le=3)
    is_active: bool = True


class ObjectiveCreate(BaseModel):
    title: str
    description: str = ""
    key_results: list[KeyResult] = []
    priority: int = Field(1, ge=1, le=3)


class OKRUpdate(BaseModel):
    key_result_id: str
    new_value: float


class OKRSummary(BaseModel):
    total: int = 0
    completed: int = 0
    on_track: int = 0
    at_risk: int = 0
