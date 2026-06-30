"""
Rule evaluator — checks conditions against current world state and triggers effects.

Rule types and their condition formats:
  tech_to_consumer:   { technology: str, state: "activated" }
  supply_to_market:   { supplier: str, metric: str, resource: str, operator: str, threshold: float }
  ecosystem_to_brand: { brand: str, metric: str, operator: str, threshold: float }
  consumer_to_brand:  { segment: str, metric: str, operator: str, threshold: float }
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.models import Rule, WorldStateData, SupplyChainLink


def evaluate_rules(
    rules: list["Rule"],
    state: "WorldStateData",
    links: list["SupplyChainLink"],
) -> list[str]:
    """
    Evaluate all rules against current world state.
    
    Returns list of newly activated rule IDs.
    """
    from engine.effects import apply_effects

    triggered = []

    for rule in rules:
        if _check_condition(rule, state, links):
            if rule.id not in state.active_rules:
                state.active_rules.append(rule.id)
                triggered.append(rule.id)
            apply_effects(rule.effect, state, links)

    return triggered


def _check_condition(rule: "Rule", state: "WorldStateData", links: list["SupplyChainLink"]) -> bool:
    """Evaluate the condition of a single rule."""
    cond = rule.condition
    rtype = rule.type

    if rtype == "tech_to_consumer":
        return _check_tech_condition(cond, state)

    if rtype == "supply_to_market":
        return _check_supply_condition(cond, state)

    if rtype == "ecosystem_to_brand":
        return _check_ecosystem_condition(cond, state)

    if rtype == "consumer_to_brand":
        return _check_consumer_condition(cond, state)

    return False


def _check_tech_condition(cond: dict, state: "WorldStateData") -> bool:
    """Check: technology X is in state Y."""
    tech_id = cond.get("technology", "")
    expected_state = cond.get("state", "activated")
    tech_status = state.technology_status.get(tech_id, {})
    if expected_state == "activated":
        return tech_status.get("activated", False)
    return False


def _check_supply_condition(cond: dict, state: "WorldStateData") -> bool:
    """Check: supplier.metric [op] threshold."""
    supplier_id = cond.get("supplier", "")
    metric = cond.get("metric", "utilization")
    resource = cond.get("resource", "")
    op = cond.get("operator", "gte")
    threshold = float(cond.get("threshold", 0))

    supplier_state = state.supplier_states.get(supplier_id, {})
    if metric == "utilization":
        util_map = supplier_state.get("utilization", {})
        actual = float(util_map.get(resource, 0))
        return _compare(actual, op, threshold)

    actual = float(supplier_state.get(metric, 0))
    return _compare(actual, op, threshold)


def _check_ecosystem_condition(cond: dict, state: "WorldStateData") -> bool:
    """Check: brand.metric [op] threshold."""
    brand_id = cond.get("brand", "")
    metric = cond.get("metric", "")
    op = cond.get("operator", "gte")
    threshold = float(cond.get("threshold", 0))

    brand_state = state.brand_states.get(brand_id, {})
    actual = float(brand_state.get(metric, 0))
    return _compare(actual, op, threshold)


def _check_consumer_condition(cond: dict, state: "WorldStateData") -> bool:
    """Check: segment.preferences.X [op] threshold."""
    segment_id = cond.get("segment", "")
    metric = cond.get("metric", "")  # e.g. "preferences.ai_assistant"

    op = cond.get("operator", "gte")
    threshold = float(cond.get("threshold", 0))

    seg = state.consumer_segments.get(segment_id, {})
    # metric is like "preferences.ai_assistant"
    parts = metric.split(".", 1)
    if len(parts) == 2 and parts[0] == "preferences":
        pref_key = parts[1]
        prefs = seg.get("current_preferences", {})
        actual = float(prefs.get(pref_key, 0))
        return _compare(actual, op, threshold)

    actual = float(seg.get(metric, 0))
    return _compare(actual, op, threshold)


def _compare(actual: float, op: str, threshold: float) -> bool:
    """Compare actual value against threshold using operator."""
    if op == "gte":
        return actual >= threshold
    if op == "lte":
        return actual <= threshold
    if op == "gt":
        return actual > threshold
    if op == "lt":
        return actual < threshold
    if op == "eq":
        return abs(actual - threshold) < 0.001
    return False
