"""Simulation (decision and result) Pydantic schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DecisionCategory(str, Enum):
    PRODUCT = "product"
    RD = "rd"
    MARKETING = "marketing"
    SUPPLY = "supply"
    FINANCE = "finance"
    HR = "hr"


class PlayerDecision(BaseModel):
    category: DecisionCategory
    action: str
    budget: Optional[float] = None
    priority: int = 1


class SimImpact(BaseModel):
    metric: str
    delta: float = 0.0
    delta_percent: float = 0.0
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    reasoning: str = ""


class QualitativeFeedback(BaseModel):
    source: str
    reaction: str
    sentiment: str  # "positive" / "negative" / "mixed"


class ChainEffect(BaseModel):
    order: int = 1  # 1=direct, 2=indirect, 3=far
    description: str
    impacts: list[SimImpact] = []
    probability: float = Field(0.5, ge=0.0, le=1.0)


class SimulationResult(BaseModel):
    turn: int = 1
    decision: PlayerDecision
    direct_impacts: list[SimImpact] = []
    qualitative_feedbacks: list[QualitativeFeedback] = []
    chain_effects: list[ChainEffect] = []
    narrative: str = ""
    risk_warnings: list[str] = []


class DecisionOption(BaseModel):
    """A pre-defined decision option available to the player."""
    id: str
    title: str
    description: str
    category: DecisionCategory
    cost: float = 0.0
    risk: int = Field(50, ge=0, le=100)
    expected_impact: list[SimImpact] = []
    prerequisites: list[str] = []
    is_locked: bool = False
    lock_reason: str = ""


class SimulateRequest(BaseModel):
    decisions: list[PlayerDecision]


class SimulateResponse(BaseModel):
    results: list[SimulationResult]
    total_cost: float = 0.0
