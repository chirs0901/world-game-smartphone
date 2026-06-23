"""AI board (agents and debate) Pydantic schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    CEO = "ceo"
    COO = "coo"
    CPO = "cpo"
    CIO = "cio"
    CFO = "cfo"
    SUPPLY_CHAIN = "supply_chain"


class RiskAppetite(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class AgentProfile(BaseModel):
    role: AgentRole
    name: str
    goal: str
    risk_appetite: RiskAppetite = RiskAppetite.MODERATE
    personality: str = ""
    expertise: list[str] = []
    relationships: dict[str, str] = {}


class AgentMemory(BaseModel):
    role: AgentRole
    recent_events: list[str] = []
    past_decisions: list[str] = []
    satisfaction: float = Field(50.0, ge=0.0, le=100.0)


class PositionStatement(BaseModel):
    role: AgentRole
    position: str  # "支持" / "反对" / "有条件支持"
    reasoning: str
    concerns: list[str] = []
    conditions: list[str] = []
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class DebateRound(BaseModel):
    round_number: int = 1
    topic: str = ""
    statements: list[PositionStatement] = []
    counter_arguments: list[dict] = []
    consensus_reached: bool = False
    summary: str = ""


class Vote(BaseModel):
    role: AgentRole
    choice: str
    reasoning: str = ""


class BoardDecision(BaseModel):
    topic: str
    options: list[str] = []
    votes: list[Vote] = []
    final_choice: str = ""
    ceo_rationale: str = ""
    dissenting_opinions: list[str] = []


class DebateRequest(BaseModel):
    topic: str
    context: str = ""
    options: list[str] = []


class DebateResponse(BaseModel):
    debate_id: str
    rounds: list[DebateRound] = []
    decision: Optional[BoardDecision] = None
    status: str = "preparing"  # preparing | debating | voting | concluded
