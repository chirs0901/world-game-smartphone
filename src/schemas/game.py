"""Game session and turn Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CompanyOption(BaseModel):
    """A selectable company for the player."""
    id: str
    name: str
    tagline: str = ""
    logo_emoji: str = "📱"
    country: str = ""
    description: str = ""
    strengths: list[str] = []
    weaknesses: list[str] = []
    strategy_hint: str = ""
    difficulty: str = "normal"
    base_metrics: dict = {}


class GameConfig(BaseModel):
    """Configuration for creating a new game."""
    company_id: str = "apple"
    difficulty: str = "normal"
    initial_cash: float = 50.0
    max_turns: int = 40


class GameSessionCreate(BaseModel):
    config: GameConfig = Field(default_factory=GameConfig)


class GameSessionResponse(BaseModel):
    id: str
    status: str
    config: GameConfig
    current_turn: int
    current_year: int
    current_quarter: int
    created_at: datetime


class TurnSummary(BaseModel):
    """Summary of a single turn, for frontend display."""
    turn: int
    year: int
    quarter: int
    events_this_turn: list[str] = []
    decisions_made: list[str] = []
    metrics_delta: dict[str, float] = {}
    narrative: str = ""


class TurnPhaseResponse(BaseModel):
    """Current phase within a turn."""
    turn: int
    phase: str  # observe | decide | execute | feedback
    year: int
    quarter: int


class MarketActivity(BaseModel):
    """A single real-time market activity tick."""
    timestamp: float
    brand: str
    action: str  # "buy" | "browse" | "switch"
    product_segment: str  # "旗舰" | "中端" | "入门"
    price: float
    quantity: int = 1
    reason: str = ""


class MarketActivitySnapshot(BaseModel):
    """Current market activity snapshot for frontend animation."""
    company_name: str = ""
    activities: list[MarketActivity] = []
    total_sales_this_quarter: float = 0.0
    total_revenue_this_quarter: float = 0.0
    market_trend: str = "stable"  # "rising" | "stable" | "declining"
    top_sellers: list[dict] = []  # [{brand, units, trend}]
