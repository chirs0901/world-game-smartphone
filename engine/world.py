"""
World class — the top-level simulation orchestrator.

Usage:
    world = World(scenario="base_2025")
    snapshot = world.tick()    # advance one quarter
    print(snapshot)
"""
from __future__ import annotations

from engine.loader import LoadedWorld
from engine.models import WorldStateData
from engine.agent import BrandAgent


class World:
    """
    The Simulation Engine's top-level orchestrator.
    
    Loads all world-model YAML, maintains runtime state,
    and executes one tick() per call.
    """

    def __init__(self, scenario: str = "base_2025"):
        loaded = LoadedWorld(scenario=scenario)
        self.state: WorldStateData = loaded.state
        self.tech_nodes = loaded.tech_nodes
        self.companies = loaded.companies
        self.segments = loaded.segments
        self.suppliers = loaded.suppliers
        self.links = loaded.links
        self.rules_list = loaded.rules
        self.indexes = loaded.indexes

        # Phase 3: Create one BrandAgent per company
        self.agents = [BrandAgent(c) for c in self.companies]

    def tick(self) -> dict:
        """
        Advance the world by one quarter.
        
        Execution order:
          1. Apply active technology effects to global baselines
          2. Evaluate all rules (conditions → effects)
          3. Apply consumer preference drift
          4. Run market simulation (brand decisions + share redistribution)
          5. Advance time
          6. Return world state snapshot
        """
        from engine.effects import apply_effects
        from engine.rules import evaluate_rules
        from engine.consumer import apply_preference_drift
        from engine.market import run_market_simulation

        # 1. Apply technology effects (only for activated nodes)
        tech_effects_applied = 0
        for tech in self.tech_nodes:
            if self.state.technology_status.get(tech.id, {}).get("activated", False):
                apply_effects(tech.effects, self.state, self.links)
                tech_effects_applied += len(tech.effects)

        # 2. Evaluate rules
        triggered_rules = evaluate_rules(self.rules_list, self.state, self.links)

        # 3. Consumer preference drift
        drift_log = apply_preference_drift(self.state, self.segments)

        # 4. Market simulation
        market_summary = run_market_simulation(
            self.state, self.companies, self.links,
            agents=self.agents,
            tech_nodes=self.tech_nodes,
            segments=self.segments,
        )

        # 5. Advance time
        self.state.advance_quarter()

        # 6. Return snapshot
        snapshot = self.state.snapshot()
        snapshot["_diagnostics"] = {
            "tech_effects_applied": tech_effects_applied,
            "triggered_rules": triggered_rules,
            "preference_drifts": drift_log,
            "market_summary": market_summary,
        }
        return snapshot

    def tick_n(self, n: int) -> list[dict]:
        """Run n ticks and return all snapshots."""
        snapshots = []
        for _ in range(n):
            snapshots.append(self.tick())
        return snapshots
