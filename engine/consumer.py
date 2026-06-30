"""
Consumer preference drift — apply trend_vectors each tick.

Every tick (1 quarter), each consumer segment's preference weights drift
by trend_vector / 4 (since trend_vectors are annual rates).

Preferences are clamped to [0.0, 1.0].
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.models import WorldStateData, ConsumerSegment


def apply_preference_drift(state: "WorldStateData", segments: list["ConsumerSegment"]) -> dict:
    """
    Apply one tick of preference drift to all consumer segments.
    
    Returns a dict of { segment_id: { preference: delta } } for logging.
    """
    drift_log: dict[str, dict[str, float]] = {}

    for seg_def in segments:
        seg_id = seg_def.id
        if seg_id not in state.consumer_segments:
            continue

        seg_state = state.consumer_segments[seg_id]
        prefs = seg_state.get("current_preferences", {})
        changes = {}

        for pref_key, annual_delta in seg_def.trend_vectors.items():
            tick_delta = annual_delta / 4.0  # annual → quarterly
            if abs(tick_delta) < 0.001:
                continue

            old_val = float(prefs.get(pref_key, 0))
            new_val = max(0.0, min(1.0, old_val + tick_delta))
            prefs[pref_key] = round(new_val, 4)
            changes[pref_key] = round(new_val - old_val, 4)

        if changes:
            drift_log[seg_id] = changes

    return drift_log
