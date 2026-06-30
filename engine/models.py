"""
Core entity types for the Simulation Engine.

All types use @dataclass for lightweight, serializable models.
The runtime world state is maintained as a mutable dict (WorldStateData).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────────────
# Atomic types
# ──────────────────────────────────────────────────────

@dataclass
class Effect:
    """A single state mutation: target + operation + value."""
    target: str            # dot-path e.g. "world.soc.performance_base"
    operation: str         # "multiply" | "add" | "set"
    value: float


@dataclass
class Resource:
    """A supplier's resource pool."""
    type: str
    total_units: float
    utilization: float
    unit_cost_usd: float


# ──────────────────────────────────────────────────────
# Entity types (match world-model YAML schemas)
# ──────────────────────────────────────────────────────

@dataclass
class TechnologyNode:
    """A technology node in the tech tree."""
    id: str
    name: str
    category: str
    tier: str                     # short_term | mid_term | long_term
    activated: bool
    prerequisites: list[str]
    unlocks: list[str]
    effects: list[Effect]
    suppliers: list[str]
    adopters: list[str]
    activation_tick: int = 0      # tick when activated


@dataclass
class CompanyAgent:
    """A brand/company with DNA-driven autonomous behavior."""
    id: str
    name: str
    country: str
    logo_emoji: str
    tagline: str
    description: str
    dna: dict[str, float]         # 7 dimensional behavior vector
    goal_function: dict           # maximize + constraints
    decision_period: int          # ticks between strategic decisions
    initial_state: dict[str, float]
    product_lineup: list[str]
    supply_chain: list[dict]
    ai_strategy: dict


@dataclass
class ConsumerSegment:
    """A consumer population segment with evolving preferences."""
    id: str
    name: str
    age_range: list[int]
    size_pct: float
    description: str
    preferences: dict[str, float]    # static base weights
    trend_vectors: dict[str, float]  # annual drift per preference


@dataclass
class SupplierDNA:
    """Supplier behavioral traits."""
    technology_lead: float
    capacity_expand: float
    profit_margin_focus: float
    customer_diversify: float
    geopolitical_risk: float


@dataclass
class SupplierAgent:
    """A component supplier with resources and tech dependencies."""
    id: str
    name: str
    country: str
    category: str
    description: str
    dna: SupplierDNA
    resources: list[dict]
    tech_dependency: list[str]


@dataclass
class SupplyChainLink:
    """A directed edge from supplier to brand."""
    id: str
    from_supplier: str            # supplier id
    to_brand: str                 # brand id
    resource_type: str
    tech_node: Optional[str]
    allocation_pct: float
    reliability: float
    cost_per_unit: float
    lead_time_quarters: int


@dataclass
class Rule:
    """A world rule: condition → effects."""
    id: str
    type: str                     # tech_to_consumer | supply_to_market | ecosystem_to_brand | consumer_to_brand
    description: str
    condition: dict               # varies by type
    effect: list[Effect]


# ──────────────────────────────────────────────────────
# Runtime state (mutable dict wrapper)
# ──────────────────────────────────────────────────────

class WorldStateData:
    """
    Mutable runtime state for a single tick.
    
    Structure matches world-model/schemas/world_state.schema.yaml:
      - global_metrics: dict { category: { metric: float } }
      - technology_status: dict { tech_id: { activated: bool, activation_tick: int } }
      - brand_states: dict { brand_id: { metric: value } }
      - supplier_states: dict { supplier_id: { utilization: {resource: float}, risk_index: float } }
      - consumer_segments: dict { segment_id: { size_pct: float, current_preferences: { pref: float } } }
      - active_rules: list[str]
      - pending_events: list[dict]
      - world_news: list[dict]
    """

    def __init__(self, tick: int = 0, year: int = 2025, quarter: int = 1):
        self.tick = tick
        self.year = year
        self.quarter = quarter
        self.global_metrics: dict = {}
        self.technology_status: dict = {}
        self.brand_states: dict = {}
        self.supplier_states: dict = {}
        self.consumer_segments: dict = {}
        self.active_rules: list[str] = []
        self.pending_events: list[dict] = []
        self.world_news: list[dict] = []

    @property
    def turn(self) -> str:
        return f"{self.year}Q{self.quarter}"

    def advance_quarter(self):
        """Increment time by one quarter."""
        self.tick += 1
        self.quarter += 1
        if self.quarter > 4:
            self.quarter = 1
            self.year += 1

    def snapshot(self) -> dict:
        """Return a deep-copied serializable dict snapshot of current state."""
        import copy
        return {
            "tick": self.tick,
            "year": self.year,
            "quarter": self.quarter,
            "turn": self.turn,
            "global_metrics": copy.deepcopy(self.global_metrics),
            "technology_status": copy.deepcopy(self.technology_status),
            "brand_states": copy.deepcopy(self.brand_states),
            "supplier_states": copy.deepcopy(self.supplier_states),
            "consumer_segments": copy.deepcopy(self.consumer_segments),
            "active_rules": list(self.active_rules),
            "pending_events": list(self.pending_events),
            "world_news": list(self.world_news),
        }
