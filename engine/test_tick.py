#!/usr/bin/env python3
"""
Verification script: load initial state, run tick(), print before/after comparison.

Usage:
    cd world-game && python3 engine/test_tick.py
"""
import sys
import os
from pathlib import Path

# Ensure engine/ can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.world import World


def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    print("=" * 60)
    print("  SMARTPHONE SIMULATION ENGINE — TICK TEST")
    print("=" * 60)

    # ── Load world ──
    world = World(scenario="base_2025")
    print(f"\nInitial state loaded: {world.state.turn}")
    print(f"  Technologies: {len(world.tech_nodes)} ({sum(1 for t in world.tech_nodes if t.activated)} activated)")
    print(f"  Brands: {len(world.companies)}")
    print(f"  Consumer segments: {len(world.segments)}")
    print(f"  Suppliers: {len(world.suppliers)}")
    print(f"  Supply chain links: {len(world.links)}")
    print(f"  Rules: {len(world.rules_list)}")

    # ── Snapshot BEFORE ──
    before = world.state.snapshot()
    before_brands = {bid: dict(bs) for bid, bs in before["brand_states"].items()}
    before_consumers = {sid: dict(cs) for sid, cs in before["consumer_segments"].items()}
    before_global = dict(before["global_metrics"])

    # ── Run one tick ──
    print_separator("EXECUTING tick()")
    result = world.tick()

    # ── Diagnostics ──
    diag = result.get("_diagnostics", {})
    print(f"\nTechnology effects applied: {diag.get('tech_effects_applied', 0)}")
    print(f"Rules triggered: {len(diag.get('triggered_rules', []))}")
    for rid in diag.get("triggered_rules", []):
        print(f"  - {rid}")

    # ── Global metrics diff ──
    print_separator("GLOBAL METRICS CHANGE")
    after_global = result["global_metrics"]
    for cat in sorted(set(list(before_global.keys()) + list(after_global.keys()))):
        before_cat = before_global.get(cat, {})
        after_cat = after_global.get(cat, {})
        for metric in sorted(set(list(before_cat.keys()) + list(after_cat.keys()))):
            bv = before_cat.get(metric, 0)
            av = after_cat.get(metric, 0)
            if abs(av - bv) > 0.01:
                delta = av - bv
                sign = "+" if delta >= 0 else ""
                print(f"  {cat}.{metric}:  {bv:.2f} → {av:.2f}  ({sign}{delta:.2f})")

    # ── Brand state diff ──
    print_separator("BRAND STATE CHANGES")
    key_metrics = ["market_share", "brand_heat", "tech_leadership", "cash_reserve",
                   "profit_margin", "supply_stability", "customer_satisfaction"]
    for brand_id in sorted(result["brand_states"].keys()):
        before_bs = before_brands.get(brand_id, {})
        after_bs = result["brand_states"].get(brand_id, {})
        changes = []
        for m in key_metrics:
            bv = before_bs.get(m, 0)
            av = after_bs.get(m, 0)
            if abs(av - bv) > 0.05:
                delta = av - bv
                sign = "+" if delta >= 0 else ""
                changes.append(f"{m}: {bv:.1f}→{av:.1f}({sign}{delta:.1f})")
        if changes:
            print(f"  {brand_id}: {', '.join(changes)}")

    # ── Consumer preference drift ──
    print_separator("CONSUMER PREFERENCE DRIFT")
    drifted = False
    for seg_id in sorted(result["consumer_segments"].keys()):
        before_seg = before_consumers.get(seg_id, {})
        after_seg = result["consumer_segments"].get(seg_id, {})
        before_prefs = before_seg.get("current_preferences", {})
        after_prefs = after_seg.get("current_preferences", {})
        changes = []
        for pref_key in sorted(set(list(before_prefs.keys()) + list(after_prefs.keys()))):
            bv = before_prefs.get(pref_key, 0)
            av = after_prefs.get(pref_key, 0)
            if abs(av - bv) > 0.001:
                delta = av - bv
                sign = "+" if delta >= 0 else ""
                changes.append(f"{pref_key}: {bv:.3f}→{av:.3f}({sign}{delta:.3f})")
        if changes:
            drifted = True
            print(f"  {seg_id}:")
            for c in changes[:5]:  # limit to top 5
                print(f"    {c}")
            if len(changes) > 5:
                print(f"    ... and {len(changes) - 5} more")
    if not drifted:
        print("  No preference changes (not all trend vectors are non-zero)")

    # ── Summary ──
    print_separator("SUMMARY")
    print(f"  Tick completed: {before['turn']} → {result['turn']}")
    print(f"  Active rules: {len(result['active_rules'])}")
    print(f"  Total brand market share: {sum(bs['market_share'] for bs in result['brand_states'].values()):.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
