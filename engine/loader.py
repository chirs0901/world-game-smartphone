"""
Load world-model YAML files into typed dataclass instances and build runtime state.

The WORLD_MODEL_DIR is relative to the engine/ directory — engine/ and world-model/
are siblings under the project root.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Optional

from engine.models import (
    Effect,
    TechnologyNode,
    CompanyAgent,
    ConsumerSegment,
    SupplierDNA,
    SupplierAgent,
    SupplyChainLink,
    Rule,
    WorldStateData,
)

# Project root = engine/../ = world-game/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORLD_MODEL_DIR = PROJECT_ROOT / "world-model"


def _load_yaml(rel_path: str) -> dict:
    """Load a YAML file relative to world-model/ directory."""
    path = WORLD_MODEL_DIR / rel_path
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


# ──────────────────────────────────────────────────────
# Entity loaders
# ──────────────────────────────────────────────────────

def load_technologies() -> list[TechnologyNode]:
    """Load technology nodes from world-model/entities/technology.schema.yaml."""
    raw = _load_yaml("entities/technology.schema.yaml")
    nodes = []
    for n in raw.get("technology_nodes", []):
        effects = [
            Effect(target=e["target"], operation=e["operation"], value=float(e["value"]))
            for e in n.get("effects", [])
        ]
        nodes.append(TechnologyNode(
            id=n["id"],
            name=n["name"],
            category=n["category"],
            tier=n.get("tier", "short_term"),
            activated=n.get("activated", False),
            prerequisites=n.get("prerequisites", []),
            unlocks=n.get("unlocks", []),
            effects=effects,
            suppliers=n.get("suppliers", []),
            adopters=n.get("adopters", []),
            activation_tick=0 if n.get("activated") else -1,
        ))
    return nodes


def load_companies() -> list[CompanyAgent]:
    """Load brand agents from world-model/entities/company.schema.yaml."""
    raw = _load_yaml("entities/company.schema.yaml")
    companies = []
    for c in raw.get("companies", []):
        companies.append(CompanyAgent(
            id=c["id"],
            name=c["name"],
            country=c["country"],
            logo_emoji=c.get("logo_emoji", ""),
            tagline=c.get("tagline", ""),
            description=c.get("description", ""),
            dna=c.get("dna", {}),
            goal_function=c.get("goal_function", {}),
            decision_period=c.get("decision_period", 4),
            initial_state=c.get("initial_state", {}),
            product_lineup=c.get("product_lineup", []),
            supply_chain=c.get("supply_chain", []),
            ai_strategy=c.get("ai_strategy", {}),
        ))
    return companies


def load_consumer_segments() -> list[ConsumerSegment]:
    """Load consumer segments from world-model/entities/consumer.schema.yaml."""
    raw = _load_yaml("entities/consumer.schema.yaml")
    segments = []
    for s in raw.get("consumer_segments", []):
        segments.append(ConsumerSegment(
            id=s["id"],
            name=s["name"],
            age_range=s.get("age_range", [18, 65]),
            size_pct=float(s.get("size_pct", 0)),
            description=s.get("description", ""),
            preferences=s.get("preferences", {}),
            trend_vectors=s.get("trend_vectors", {}),
        ))
    return segments


def load_suppliers() -> list[SupplierAgent]:
    """Load supplier agents from world-model/entities/supply_chain.schema.yaml."""
    raw = _load_yaml("entities/supply_chain.schema.yaml")
    suppliers = []
    for s in raw.get("suppliers", []):
        dna_raw = s.get("dna", {})
        dna = SupplierDNA(
            technology_lead=float(dna_raw.get("technology_lead", 0.5)),
            capacity_expand=float(dna_raw.get("capacity_expand", 0.5)),
            profit_margin_focus=float(dna_raw.get("profit_margin_focus", 0.5)),
            customer_diversify=float(dna_raw.get("customer_diversify", 0.5)),
            geopolitical_risk=float(dna_raw.get("geopolitical_risk", 0.3)),
        )
        suppliers.append(SupplierAgent(
            id=s["id"],
            name=s["name"],
            country=s["country"],
            category=s["category"],
            description=s.get("description", ""),
            dna=dna,
            resources=s.get("resources", []),
            tech_dependency=s.get("tech_dependency", []),
        ))
    return suppliers


def load_supply_chain_links() -> list[SupplyChainLink]:
    """Load supply chain links from world-model/entities/supply_chain.schema.yaml."""
    raw = _load_yaml("entities/supply_chain.schema.yaml")
    links = []
    for l in raw.get("links", []):
        links.append(SupplyChainLink(
            id=l["id"],
            from_supplier=l["from"],
            to_brand=l["to"],
            resource_type=l["resource_type"],
            tech_node=l.get("tech_node"),
            allocation_pct=float(l.get("allocation_pct", 0)),
            reliability=float(l.get("reliability", 0.8)),
            cost_per_unit=float(l.get("cost_per_unit", 0)),
            lead_time_quarters=int(l.get("lead_time_quarters", 2)),
        ))
    return links


def load_rules(scenario: str = "base_2025") -> list[Rule]:
    """Load system rules + scenario-specific rules."""
    raw = _load_yaml("rules/system.rules.yaml")
    rules = []
    for r in raw.get("rules", []):
        effects = [
            Effect(target=e["target"], operation=e["operation"], value=float(e["value"]))
            for e in r.get("effect", [])
        ]
        rules.append(Rule(
            id=r["id"],
            type=r["type"],
            description=r.get("description", ""),
            condition=r.get("condition", {}),
            effect=effects,
        ))

    # Load scenario rules
    scenario_raw = _load_yaml(f"rules/scenario/{scenario}.rules.yaml")
    for r in scenario_raw.get("rules", []):
        effects = [
            Effect(target=e["target"], operation=e["operation"], value=float(e["value"]))
            for e in r.get("effect", [])
        ]
        rules.append(Rule(
            id=r["id"],
            type=r["type"],
            description=r.get("description", ""),
            condition=r.get("condition", {}),
            effect=effects,
        ))

    return rules


# ──────────────────────────────────────────────────────
# Index builders
# ──────────────────────────────────────────────────────

def build_indexes(
    tech_nodes: list[TechnologyNode],
    companies: list[CompanyAgent],
    segments: list[ConsumerSegment],
    suppliers: list[SupplierAgent],
    links: list[SupplyChainLink],
) -> dict:
    """Build lookup dicts for fast cross-referencing."""
    return {
        "tech_by_id": {n.id: n for n in tech_nodes},
        "brands_by_id": {c.id: c for c in companies},
        "segments_by_id": {s.id: s for s in segments},
        "suppliers_by_id": {s.id: s for s in suppliers},
        "links_by_supplier": _group_links_by(links, "from_supplier"),
        "links_by_brand": _group_links_by(links, "to_brand"),
        "links_by_tech": _group_links_by_tech(links),
    }


def _group_links_by(links: list[SupplyChainLink], attr: str) -> dict[str, list[SupplyChainLink]]:
    """Group supply chain links by a given attribute."""
    result: dict[str, list[SupplyChainLink]] = {}
    for link in links:
        key = getattr(link, attr)
        result.setdefault(key, []).append(link)
    return result


def _group_links_by_tech(links: list[SupplyChainLink]) -> dict[str, list[SupplyChainLink]]:
    """Group links by tech_node, skipping None."""
    result: dict[str, list[SupplyChainLink]] = {}
    for link in links:
        if link.tech_node:
            result.setdefault(link.tech_node, []).append(link)
    return result


# ──────────────────────────────────────────────────────
# Initial state builder
# ──────────────────────────────────────────────────────

def load_initial_state(
    scenario: str = "base_2025",
    companies: Optional[list[CompanyAgent]] = None,
    segments: Optional[list[ConsumerSegment]] = None,
    suppliers: Optional[list[SupplierAgent]] = None,
    links: Optional[list[SupplyChainLink]] = None,
    tech_nodes: Optional[list[TechnologyNode]] = None,
) -> WorldStateData:
    """Load initial world state from YAML and populate WorldStateData."""
    # Map scenario names to initial state files
    scenario_file_map = {
        "base_2025": "2025Q1.world.yaml",
    }
    filename = scenario_file_map.get(scenario, f"{scenario}.world.yaml")
    raw = _load_yaml(f"initial_states/{filename}")

    state = WorldStateData(
        tick=int(raw.get("tick", 0)),
        year=int(raw.get("year", 2025)),
        quarter=int(raw.get("quarter", 1)),
    )

    # Technology status
    for tech_id, activated in raw.get("technology_activation", {}).items():
        state.technology_status[tech_id] = {
            "activated": bool(activated),
            "activation_tick": 0 if activated else -1,
        }

    # Global baselines
    state.global_metrics = _deep_copy_dict(raw.get("global_baselines", {}))
    if state.global_metrics:
        # Nest flat baselines into category.sub_metric structure
        # e.g. soc_performance → global_metrics.soc.performance_base
        nested = _nest_baselines(state.global_metrics)
        state.global_metrics = nested

    # Brand states: initial_state YAML uses short ids (apple, samsung, ...)
    # but engine uses long ids (brand_apple, brand_samsung, ...)
    for brand_id_short, brand_data in raw.get("brands", {}).items():
        brand_id = brand_id_short if brand_id_short.startswith("brand_") else f"brand_{brand_id_short}"
        state.brand_states[brand_id] = dict(brand_data)
        # Add derivative fields if missing
        state.brand_states[brand_id].setdefault("ecosystem_strength", 50.0)
        state.brand_states[brand_id].setdefault("customer_retention_rate", 0.5)
        state.brand_states[brand_id].setdefault("self_sufficiency_index", 30.0)
        state.brand_states[brand_id].setdefault("iot_ecosystem_devices", 10.0)
        state.brand_states[brand_id].setdefault("soc_cost", 100.0)
        state.brand_states[brand_id].setdefault("competitive_advantage_index", 50.0)
        state.brand_states[brand_id].setdefault("ai_capability", 50.0)

    # Supplier states
    for supplier_id, supplier_data in raw.get("suppliers", {}).items():
        resources = supplier_data.get("resources", {})
        utilization_map = {}
        for res_name, res_data in resources.items():
            utilization_map[res_name] = float(res_data.get("utilization", 0.5))
        state.supplier_states[supplier_id] = {
            "utilization": utilization_map,
            "risk_index": 0.3,  # default
        }

    # Consumer segments: load from YAML definitions (not initial_state —
    # the initial_state only has brand/supplier/tech data).
    # Preferences start at their static base values defined in consumer.schema.yaml.
    if segments:
        for seg in segments:
            state.consumer_segments[seg.id] = {
                "size_pct": seg.size_pct,
                "current_preferences": dict(seg.preferences),
            }

    return state


def _deep_copy_dict(d: dict) -> dict:
    """Simple deep copy for nested dicts of primitives."""
    import copy
    return copy.deepcopy(d)


def _nest_baselines(flat: dict) -> dict:
    """
    Convert flat global_baselines (e.g. soc_performance) to nested structure
    (e.g. {"soc": {"performance_base": value}}).
    
    Mapping:
      soc_performance           → soc.performance_base
      soc_power_efficiency      → soc.power_efficiency_base
      soc_cost_per_die          → soc.cost_per_die_base
      battery_energy_density    → battery.energy_density_whl
      battery_cost_per_mah      → battery.cost_per_mah
      display_peak_brightness   → display.peak_brightness_nit
      display_power_efficiency  → display.power_efficiency
      camera_zoom_capability    → camera.zoom_capability_index
      camera_module_cost        → camera.module_cost
      ai_on_device_capability   → ai.on_device_capability_index
    """
    mapping = {
        "soc_performance": ("soc", "performance_base"),
        "soc_power_efficiency": ("soc", "power_efficiency_base"),
        "soc_cost_per_die": ("soc", "cost_per_die_base"),
        "battery_energy_density": ("battery", "energy_density_whl"),
        "battery_cost_per_mah": ("battery", "cost_per_mah"),
        "display_peak_brightness": ("display", "peak_brightness_nit"),
        "display_power_efficiency": ("display", "power_efficiency"),
        "camera_zoom_capability": ("camera", "zoom_capability_index"),
        "camera_module_cost": ("camera", "module_cost"),
        "ai_on_device_capability": ("ai", "on_device_capability_index"),
    }
    nested: dict = {}
    for flat_key, value in flat.items():
        if flat_key in mapping:
            cat, metric = mapping[flat_key]
            nested.setdefault(cat, {})[metric] = float(value)
    return nested


# ──────────────────────────────────────────────────────
# Convenience: load everything at once
# ──────────────────────────────────────────────────────

class LoadedWorld:
    """All loaded entities + initial state + indexes, ready for World construction."""

    def __init__(self, scenario: str = "base_2025"):
        self.scenario = scenario
        self.tech_nodes = load_technologies()
        self.companies = load_companies()
        self.segments = load_consumer_segments()
        self.suppliers = load_suppliers()
        self.links = load_supply_chain_links()
        self.rules = load_rules(scenario)
        self.state = load_initial_state(
            scenario=scenario,
            companies=self.companies,
            segments=self.segments,
            suppliers=self.suppliers,
            links=self.links,
            tech_nodes=self.tech_nodes,
        )
        self.indexes = build_indexes(
            self.tech_nodes, self.companies, self.segments,
            self.suppliers, self.links,
        )
