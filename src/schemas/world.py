"""World state Pydantic schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    BRAND = "brand"
    SUPPLIER = "supplier"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    PERSON = "person"


class EntityRelation(BaseModel):
    target_id: str
    relation_type: str  # "competes_with", "supplies", "uses_tech", etc.
    weight: float = 1.0
    attributes: dict = {}


class Entity(BaseModel):
    id: str
    type: EntityType
    name: str
    attributes: dict = {}
    relations: list[EntityRelation] = []


class BrandMetrics(BaseModel):
    """Player brand quantitative state snapshot."""
    sales_volume: float = 0.0          # 万台
    revenue: float = 0.0              # 亿元
    profit: float = 0.0               # 亿元
    inventory: float = 0.0            # 万台
    cash_reserve: float = 50.0        # 亿元
    brand_heat: float = Field(50.0, ge=0.0, le=100.0)
    tech_leadership: float = Field(50.0, ge=0.0, le=100.0)
    market_share: float = Field(5.0, ge=0.0, le=100.0)
    supply_stability: float = Field(70.0, ge=0.0, le=100.0)
    customer_satisfaction: float = Field(60.0, ge=0.0, le=100.0)
    morale: float = Field(70.0, ge=0.0, le=100.0)


class MarketMetrics(BaseModel):
    """Industry-wide market indicators."""
    total_market_size: float = 120000.0  # 万台
    growth_rate: float = 0.02
    avg_selling_price: float = 3200.0    # 元
    top_brands: list[dict] = []


class WorldState(BaseModel):
    """Complete world state for a given turn."""
    turn: int = 1
    year: int = 2025
    quarter: int = 1
    brand_metrics: BrandMetrics = Field(default_factory=BrandMetrics)
    market_metrics: MarketMetrics = Field(default_factory=MarketMetrics)
    active_events: list[str] = []
    entities_snapshot: dict[str, Entity] = {}


class MetricChange(BaseModel):
    old_value: float
    new_value: float
    delta: float
    reasons: list[str] = []


class TurnDelta(BaseModel):
    """Records all metric changes and their reasons for a single turn."""
    metric_changes: dict[str, MetricChange] = {}


class KnowledgeGraphResponse(BaseModel):
    """Response for knowledge graph visualization."""
    nodes: list[dict] = []
    edges: list[dict] = []
