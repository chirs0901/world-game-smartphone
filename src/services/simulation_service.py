"""Simulation service — orchestrates decision simulation."""

from typing import Optional

from src.engines.rss_intel import RSSIntelEngine
from src.engines.simulation import SimulationEngine
from src.engines.knowledge_graph import KnowledgeGraph
from src.llm.client import LLMClient
from src.schemas.intel import GameEvent
from src.schemas.simulation import PlayerDecision, SimulationResult
from src.schemas.world import WorldState
from src.services.rss_service import RSSService


class SimulationService:
    """Orchestrates simulation runs."""

    def __init__(
        self,
        rss_service: Optional[RSSService] = None,
        rss_intel_engine: Optional[RSSIntelEngine] = None,
    ):
        self.kg = KnowledgeGraph()
        self.rss_service = rss_service or RSSService()
        self.rss_intel_engine = rss_intel_engine or RSSIntelEngine()
        self.engine = SimulationEngine(
            kg=self.kg,
            rss_service=self.rss_service,
            rss_intel_engine=self.rss_intel_engine,
        )

    async def simulate_decisions(
        self,
        decisions: list[PlayerDecision],
        state: WorldState,
        active_events: list[GameEvent],
    ) -> list[SimulationResult]:
        """Simulate multiple decisions sequentially."""
        results = []
        for decision in sorted(decisions, key=lambda d: d.priority):
            result = await self.engine.simulate(decision, state, active_events)
            results.append(result)
        return results
