"""
Market simulation — brand agents make strategic decisions, market share redistributes.

Phase 3 upgrade:
  - BrandAgent.decide() called on each agent's decision_period.
  - Off-cycle: maintenance (brand_heat decay, supply_stability drift).
  - Market share redistribution based on competitiveness scores (unchanged).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.models import WorldStateData, SupplyChainLink, CompanyAgent, TechnologyNode, ConsumerSegment
    from engine.agent import BrandAgent


def run_market_simulation(
    state: "WorldStateData",
    companies: list["CompanyAgent"],
    links: list["SupplyChainLink"],
    agents: list["BrandAgent"],
    tech_nodes: list["TechnologyNode"],
    segments: list["ConsumerSegment"],
) -> dict:
    """
    Execute one tick of market simulation.

    1. Each brand agent decides (if on-cycle) or gets maintenance (off-cycle).
    2. Calculate competitiveness scores.
    3. Redistribute market shares.

    Returns a summary dict for logging.
    """
    brand_map = {c.id: c for c in companies}
    decision_log: dict[str, dict] = {}

    # Step 1: Brand decisions (on-cycle) or maintenance (off-cycle)
    for agent in agents:
        brand_id = agent.id
        brand_state = state.brand_states.get(brand_id)
        if brand_state is None:
            continue

        if agent.should_decide(state.tick):
            trace = agent.decide(state, links, tech_nodes, segments)
            decision_log[brand_id] = trace
        else:
            _maintenance(brand_id, brand_state, links)

    # Step 2: Compute competitiveness scores
    scores = {}
    for brand_id, brand_state in state.brand_states.items():
        scores[brand_id] = _competitiveness(brand_state)

    # Step 3: Redistribute market share (simple weighted allocation)
    total_score = sum(scores.values())
    if total_score > 0:
        for brand_id, brand_state in state.brand_states.items():
            target_share = (scores[brand_id] / total_score) * 100.0
            old_share = brand_state.get("market_share", 0)
            # Smooth transition: move 30% toward target each tick
            new_share = old_share + (target_share - old_share) * 0.3
            brand_state["market_share"] = round(max(0.1, new_share), 2)

            # Update quarterly shipment based on market share
            brand_state["quarterly_shipment"] = round(
                brand_state["market_share"] * 35, 0  # ~3500万台 total market
            )

    return {
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "decisions": {k: _summary(v) for k, v in decision_log.items()},
    }


def _maintenance(
    brand_id: str,
    brand_state: dict,
    links: list["SupplyChainLink"],
):
    """Off-cycle maintenance: natural decay and minor adjustments."""

    # Brand heat decays slowly
    tech = brand_state.get("tech_leadership", 50)
    csat = brand_state.get("customer_satisfaction", 50)
    brand_state["brand_heat"] = round(
        brand_state.get("brand_heat", 50) * 0.98 + (tech * 0.02 + csat * 0.01), 2
    )
    brand_state["brand_heat"] = min(100, max(0, brand_state["brand_heat"]))

    # Supply stability drifts toward link reliability
    brand_links = [l for l in links if l.to_brand == brand_id]
    if brand_links:
        avg_reliability = sum(l.reliability for l in brand_links) / len(brand_links)
        brand_state["supply_stability"] = round(
            brand_state.get("supply_stability", 50) * 0.95 + avg_reliability * 100 * 0.05, 2
        )


def _competitiveness(brand_state: dict) -> float:
    """
    Calculate a brand's competitiveness score (0-100 scale).

    Weighted combination of:
      - brand_heat x 0.30
      - tech_leadership x 0.25
      - price_competitiveness x 0.25 (inverse of profit_margin)
      - customer_satisfaction x 0.20
    """
    brand_heat = brand_state.get("brand_heat", 50) / 100.0
    tech = brand_state.get("tech_leadership", 50) / 100.0
    margin = brand_state.get("profit_margin", 15)
    # Price competitiveness: lower margin = more competitive pricing
    price_comp = max(0, 1.0 - margin / 60.0)
    csat = brand_state.get("customer_satisfaction", 50) / 100.0

    score = (
        brand_heat * 0.30
        + tech * 0.25
        + price_comp * 0.25
        + csat * 0.20
    ) * 100.0

    return max(1.0, score)


def _summary(trace: dict) -> dict:
    """Extract a compact summary from a decision trace."""
    return {
        "tick": trace.get("tick"),
        "tech_investment": trace.get("tech_investment", {}).get("chosen"),
        "pricing": trace.get("pricing", {}).get("chosen"),
        "supply": trace.get("supply", {}).get("chosen"),
    }
