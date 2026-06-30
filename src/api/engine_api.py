"""Engine API — wraps the World simulation engine as REST endpoints.

Attached to the existing FastAPI server at /api/engine/*.
The World instance is a singleton, loaded on first access.
"""
from __future__ import annotations

from fastapi import APIRouter

from engine.world import World

router = APIRouter(prefix="/engine", tags=["Engine"])

_world: World | None = None


def get_world() -> World:
    """Lazy-load the World singleton."""
    global _world
    if _world is None:
        _world = World(scenario="base_2025")
    return _world


# ─────────────────────────────────────────────
# GET /api/engine/world — full world snapshot
# ─────────────────────────────────────────────

@router.get("/world")
def get_world_snapshot():
    """Return the current full world state snapshot."""
    w = get_world()
    return w.state.snapshot()


# ─────────────────────────────────────────────
# POST /api/engine/tick — advance one quarter
# ─────────────────────────────────────────────

@router.post("/tick")
def tick():
    """Advance the world by one quarter. Returns compact summary."""
    w = get_world()
    snapshot = w.tick()
    diag = snapshot.get("_diagnostics", {})

    # Top 3 brands by market share
    brands = snapshot.get("brand_states", {})
    ranked = sorted(
        brands.items(),
        key=lambda kv: kv[1].get("market_share", 0),
        reverse=True,
    )
    top_market = [
        {
            "id": bid,
            "name": bid.replace("brand_", "").capitalize(),
            "market_share": bs.get("market_share", 0),
            "tech_leadership": bs.get("tech_leadership", 0),
            "profit_margin": bs.get("profit_margin", 0),
        }
        for bid, bs in ranked[:3]
    ]

    # Decision summaries — only agents that decided THIS tick
    ms_decisions = diag.get("market_summary", {}).get("decisions", {})
    decisions = {}
    for bid, summary in ms_decisions.items():
        bs = brands.get(bid, {})
        ld = bs.get("last_decision", {})
        decisions[bid] = {
            "tech_investment": summary.get("tech_investment"),
            "pricing": summary.get("pricing"),
            "supply": summary.get("supply"),
            "effects": ld.get("effects", []),
        }

    return {
        "turn": snapshot.get("turn"),
        "tick": snapshot.get("tick"),
        "diagnostics": {
            "tech_effects_applied": diag.get("tech_effects_applied", 0),
            "triggered_rules": diag.get("triggered_rules", 0),
        },
        "decisions": decisions,
        "top_market": top_market,
        "brands": {
            bid: {
                "market_share": bs.get("market_share"),
                "tech_leadership": bs.get("tech_leadership"),
                "profit_margin": bs.get("profit_margin"),
                "brand_heat": bs.get("brand_heat"),
                "supply_stability": bs.get("supply_stability"),
                "customer_satisfaction": bs.get("customer_satisfaction"),
                "cash_reserve": bs.get("cash_reserve"),
                "last_decision": bs.get("last_decision"),
            }
            for bid, bs in brands.items()
        },
    }


# ─────────────────────────────────────────────
# GET /api/engine/brands — brand states
# ─────────────────────────────────────────────

@router.get("/brands")
def list_brands():
    """Return all brand states with their last decision."""
    w = get_world()
    state = w.state
    brands = state.brand_states

    result = []
    for bid, bs in brands.items():
        company = _find_company(w, bid)
        entry = {
            "id": bid,
            "name": company.name if company else bid,
            "country": company.country if company else "",
            "decision_period": company.decision_period if company else 2,
            "market_share": bs.get("market_share"),
            "tech_leadership": bs.get("tech_leadership"),
            "brand_heat": bs.get("brand_heat"),
            "profit_margin": bs.get("profit_margin"),
            "supply_stability": bs.get("supply_stability"),
            "customer_satisfaction": bs.get("customer_satisfaction"),
            "cash_reserve": bs.get("cash_reserve"),
            "quarterly_shipment": bs.get("quarterly_shipment"),
            "last_decision": bs.get("last_decision"),
        }
        result.append(entry)

    # Sort by market_share descending
    result.sort(key=lambda b: b["market_share"] or 0, reverse=True)

    return {
        "turn": state.turn,
        "tick": state.tick,
        "brands": result,
    }


# ─────────────────────────────────────────────
# GET /api/engine/tech — technology status
# ─────────────────────────────────────────────

@router.get("/tech")
def list_tech():
    """Return technology node statuses."""
    w = get_world()
    state = w.state

    result = []
    for tech in w.tech_nodes:
        status = state.technology_status.get(tech.id, {})
        result.append({
            "id": tech.id,
            "name": tech.name,
            "category": tech.category,
            "tier": tech.tier,
            "activated": status.get("activated", False),
            "effect_count": len(tech.effects),
            "unlocks": tech.unlocks,
            "adopters": tech.adopters,
            "suppliers": tech.suppliers,
        })

    return {
        "turn": state.turn,
        "tech_nodes": result,
    }


# ─────────────────────────────────────────────
# POST /api/engine/reset — reset the world
# ─────────────────────────────────────────────

@router.post("/reset")
def reset_world(scenario: str = "base_2025"):
    """Reset the world to its initial state (reload YAML)."""
    global _world
    _world = World(scenario=scenario)
    return {
        "message": f"World reset to {scenario}",
        "turn": _world.state.turn,
        "brands": len(_world.companies),
        "tech_nodes": len(_world.tech_nodes),
    }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _find_company(w: World, brand_id: str):
    """Find a CompanyAgent by brand_id."""
    for c in w.companies:
        if c.id == brand_id:
            return c
    return None
