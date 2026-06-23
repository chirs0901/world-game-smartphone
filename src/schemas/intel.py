"""Intel (news and events) Pydantic schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NewsCategory(str, Enum):
    MARKET = "market"
    TECHNOLOGY = "technology"
    SUPPLY_CHAIN = "supply_chain"
    POLICY = "policy"
    COMPETITOR = "competitor"
    CONSUMER = "consumer"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class EventSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NewsItem(BaseModel):
    id: str = ""
    turn: int = 1
    category: NewsCategory = NewsCategory.MARKET
    headline: str
    content: str
    source: str = ""
    sentiment: Sentiment = Sentiment.NEUTRAL
    affected_entities: list[str] = []
    is_critical: bool = False
    tags: list[str] = []


class EventImpact(BaseModel):
    metric: str
    direction: str  # "up" / "down"
    magnitude: str  # "small" / "medium" / "large"
    estimated_value: Optional[float] = None
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class GameEvent(BaseModel):
    id: str = ""
    turn: int = 1
    category: NewsCategory = NewsCategory.MARKET
    severity: EventSeverity = EventSeverity.MEDIUM
    title: str
    description: str
    impacts: list[EventImpact] = []
    response_options: list[str] = []
    chain_effects: list[str] = []
    duration_turns: int = 1
    # RSS 来源字段 (可选, 由 RSS 情报驱动时填充)
    source_rss: str = ""
    source_link: str = ""
    component_id: Optional[str] = None
    tech_tags: list[str] = []
    sentiment: str = ""
    rss_driven: bool = False


class EventDetail(GameEvent):
    full_analysis: str = ""
    related_events: list[str] = []
    recommended_actions: list[str] = []
