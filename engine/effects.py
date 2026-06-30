"""
Effect interpreter — the core state mutation engine.

All world changes flow through this module as Effect tuples:
  { target: dot-path, operation: multiply|add|set, value: float }

Compound target patterns (resolved at runtime against current state):
  - brands_using_tsmc_3nm.*         → brands linked to TSMC 3nm capacity
  - brands_using_tsmc_4nm.*         → brands linked to TSMC 4nm capacity
  - brands_not_using_tsmc.*         → brands NOT linked to TSMC
  - brands_with_ai_index_below_N.*  → brands with ai_capability < N
  - brands_with_ai_index_above_N.*  → brands with ai_capability > N
  - brands_without_foldable.*       → brands without foldable in lineup
  - segment_all.*                   → all consumer segments
  - competitor_android_brands.*     → all brands except Apple
  - all_linked_brands.*             → all brands linked to a specific supplier
  - mid_range_phones.*              → brands in mid-range tier (tech_leadership 40-65)
  - competitor_brands.*             → brands not directly affected
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.models import Effect, WorldStateData, SupplyChainLink


def apply_effect(effect: Effect, state: "WorldStateData", links: list["SupplyChainLink"]) -> list[str]:
    """
    Apply a single Effect to the world state.
    
    Returns list of concrete target paths that were modified (for logging).
    """
    targets = _resolve_target(effect.target, state, links)
    modified = []
    for resolved_path in targets:
        _apply_operation(state, resolved_path, effect.operation, effect.value)
        modified.append(resolved_path)
    return modified


def apply_effects(effects: list["Effect"], state: "WorldStateData", links: list["SupplyChainLink"]) -> list[str]:
    """Apply a list of Effects. Returns all modified paths."""
    all_modified = []
    for effect in effects:
        all_modified.extend(apply_effect(effect, state, links))
    return all_modified


# ──────────────────────────────────────────────────────
# Target resolution
# ──────────────────────────────────────────────────────

def _resolve_target(target: str, state: "WorldStateData", links: list["SupplyChainLink"]) -> list[str]:
    """
    Resolve a compound target to a list of concrete dot-paths.
    
    Simple targets (e.g. "brand_apple.market_share") return as-is.
    Compound targets (e.g. "brands_using_tsmc_3nm.soc_cost") expand to
    all matching brand paths.
    """
    parts = target.split(".", 1)
    prefix = parts[0]
    suffix = parts[1] if len(parts) > 1 else ""

    # ── Simple single-entity targets ──
    if prefix.startswith("brand_") and prefix in state.brand_states:
        return [target]
    if prefix.startswith("segment_") and prefix in state.consumer_segments:
        return [target]
    if prefix.startswith("supplier_") and prefix in state.supplier_states:
        return [target]
    if prefix == "world":
        return [target]
    if prefix == "tech":
        return [target]  # e.g. "tech.mid_chip.competitiveness_index"

    # ── Compound targets ──

    # segment_all: apply to all consumer segments
    if prefix == "segment_all":
        return [f"{seg_id}.{suffix}" for seg_id in state.consumer_segments]

    # competitor_android_brands: all brands except Apple
    if prefix == "competitor_android_brands":
        return [f"{bid}.{suffix}" for bid in state.brand_states if bid != "brand_apple"]

    # brands_using_tsmc_3nm / brands_using_tsmc_4nm
    if prefix.startswith("brands_using_tsmc_"):
        node = prefix.replace("brands_using_tsmc_", "")
        brand_ids = _brands_linked_to_tsmc(links, node)
        return [f"{bid}.{suffix}" for bid in brand_ids if bid in state.brand_states]

    # brands_not_using_tsmc
    if prefix == "brands_not_using_tsmc":
        using_tsmc = set()
        for link in links:
            if link.from_supplier == "supplier_tsmc":
                using_tsmc.add(link.to_brand)
        return [f"{bid}.{suffix}" for bid in state.brand_states if bid not in using_tsmc]

    # brands_with_ai_index_below_N / brands_with_ai_index_above_N
    if prefix.startswith("brands_with_ai_index_below_"):
        threshold = float(prefix.replace("brands_with_ai_index_below_", ""))
        return [
            f"{bid}.{suffix}" for bid, bs in state.brand_states.items()
            if bs.get("ai_capability", 50) < threshold
        ]
    if prefix.startswith("brands_with_ai_index_above_"):
        threshold = float(prefix.replace("brands_with_ai_index_above_", ""))
        return [
            f"{bid}.{suffix}" for bid, bs in state.brand_states.items()
            if bs.get("ai_capability", 50) > threshold
        ]

    # brands_without_foldable
    if prefix == "brands_without_foldable":
        return [
            f"{bid}.{suffix}" for bid, bs in state.brand_states.items()
            if not any("fold" in p.lower() or "z_fold" in p.lower()
                       for p in bs.get("product_lineup", []))
        ]

    # all_linked_brands — used with propagation rules, resolve from context
    if prefix == "all_linked_brands":
        return [f"{bid}.{suffix}" for bid in state.brand_states]

    # competitor_brands — used with propagation rules
    if prefix == "competitor_brands":
        return [f"{bid}.{suffix}" for bid in state.brand_states]

    # mid_range_phones: brands with tech_leadership between 40 and 65
    if prefix == "mid_range_phones":
        return [
            f"{bid}.{suffix}" for bid, bs in state.brand_states.items()
            if 40 <= bs.get("tech_leadership", 50) <= 65
        ]

    # affected_brand / affected_links — propagation context, fallback to all brands
    if prefix in ("affected_brand", "affected_links"):
        return [f"{bid}.{suffix}" for bid in state.brand_states]

    # Unknown prefix — return as-is (might be a flat global metric)
    return [target]


def _brands_linked_to_tsmc(links: list["SupplyChainLink"], node: str) -> set[str]:
    """Find brands linked to TSMC for a specific process node (3nm or 4nm)."""
    node_map = {"3nm": "3nm_wafer_capacity", "4nm": "4nm_wafer_capacity"}
    resource = node_map.get(node, f"{node}_wafer_capacity")
    return {
        link.to_brand for link in links
        if link.from_supplier == "supplier_tsmc" and link.resource_type == resource
    }


# ──────────────────────────────────────────────────────
# Operation application
# ──────────────────────────────────────────────────────

def _apply_operation(state: "WorldStateData", path: str, operation: str, value: float):
    """Apply an operation to a dot-path in the state."""
    parts = path.split(".")

    # Navigate to the parent dict and get the final key
    if parts[0] == "world":
        current = state.global_metrics
        for part in parts[1:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        final_key = parts[-1]
    elif parts[0].startswith("brand_"):
        brand_id = parts[0]
        if brand_id not in state.brand_states:
            state.brand_states[brand_id] = {}
        current = state.brand_states[brand_id]
        for part in parts[1:-1]:
            if isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]
            else:
                return  # cannot navigate into non-dict
        final_key = parts[-1]
    elif parts[0].startswith("segment_"):
        seg_id = parts[0]
        if seg_id not in state.consumer_segments:
            return
        seg = state.consumer_segments[seg_id]
        # segment targets go into current_preferences
        if len(parts) >= 3 and parts[1] == "preferences":
            pref_key = parts[2] if len(parts) > 2 else final_key
            final_key = parts[2] if len(parts) == 3 else parts[-1]
            current = seg.get("current_preferences", {})
        else:
            current = seg
            for part in parts[1:-1]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return
            final_key = parts[-1]
    elif parts[0].startswith("supplier_"):
        sup_id = parts[0]
        if sup_id not in state.supplier_states:
            return
        current = state.supplier_states[sup_id]
        for part in parts[1:-1]:
            if isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]
            else:
                return
        final_key = parts[-1]
    else:
        # Flat target (e.g., "mid_range_phones.panel_cost")
        return

    # Execute operation
    if isinstance(current, dict) and final_key in current:
        old_val = float(current.get(final_key, 0))
        if operation == "multiply":
            current[final_key] = round(old_val * value, 4)
        elif operation == "add":
            current[final_key] = round(old_val + value, 4)
        elif operation == "set":
            current[final_key] = value
    elif isinstance(current, dict):
        # Key doesn't exist yet — initialize
        if operation == "set":
            current[final_key] = value
        elif operation == "add":
            current[final_key] = value
        elif operation == "multiply":
            current[final_key] = 100.0 * value  # assume baseline 100


def resolve_metric(state: "WorldStateData", path: str) -> float:
    """Read a value from state by dot-path. Returns 0.0 if not found."""
    parts = path.split(".")

    if parts[0] == "world":
        current = state.global_metrics
        for part in parts[1:]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return 0.0
        return float(current) if isinstance(current, (int, float)) else 0.0

    if parts[0].startswith("brand_"):
        brand_id = parts[0]
        if brand_id not in state.brand_states:
            return 0.0
        current = state.brand_states[brand_id]
        for part in parts[1:]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return 0.0
        return float(current) if isinstance(current, (int, float)) else 0.0

    if parts[0].startswith("segment_"):
        seg_id = parts[0]
        if seg_id not in state.consumer_segments:
            return 0.0
        seg = state.consumer_segments[seg_id]
        if len(parts) >= 3 and parts[1] == "preferences":
            prefs = seg.get("current_preferences", {})
            return float(prefs.get(parts[2], 0.0))
        current = seg
        for part in parts[1:]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return 0.0
        return float(current) if isinstance(current, (int, float)) else 0.0

    if parts[0].startswith("supplier_"):
        sup_id = parts[0]
        if sup_id not in state.supplier_states:
            return 0.0
        current = state.supplier_states[sup_id]
        for part in parts[1:]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return 0.0
        if isinstance(current, dict):
            # e.g., utilization.3nm_wafer_capacity
            return 0.0
        return float(current) if isinstance(current, (int, float)) else 0.0

    return 0.0
