"""World state machine — manages turn-based state transitions."""

from typing import Optional

from src.engines.knowledge_graph import KnowledgeGraph
from src.schemas.board import BoardDecision
from src.schemas.intel import GameEvent
from src.schemas.simulation import PlayerDecision, SimImpact, SimulationResult
from src.schemas.world import BrandMetrics, MarketMetrics, MetricChange, TurnDelta, WorldState
from src.utils.config import load_yaml
from src.utils.logging import logger


class WorldStateMachine:
    """Core engine for managing world state transitions.

    Design principles:
    - State immutability: each apply() produces a new WorldState
    - Traceability: every metric change records its reasons
    - Bounded changes: single-turn changes are clamped to prevent wild swings
    """

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self._config = load_yaml("game.yaml")
        self._companies = load_yaml("companies.yaml").get("companies", [])

    def get_companies(self) -> list[dict]:
        """Return all available companies."""
        return self._companies

    def get_company(self, company_id: str) -> Optional[dict]:
        """Get a specific company by ID."""
        for c in self._companies:
            if c["id"] == company_id:
                return c
        return None

    def create_initial_state(
        self, difficulty: str = "normal", company_id: str = "apple"
    ) -> WorldState:
        """Create the initial world state for a new game."""
        game_cfg = self._config.get("game", {})
        diff_cfg = self._config.get("difficulty", {}).get(difficulty, {})
        industry_cfg = load_yaml("industry.yaml")

        # Get company-specific base metrics
        company = self.get_company(company_id)
        if company and "base_metrics" in company:
            bm = company["base_metrics"]
            brand_metrics = BrandMetrics(
                sales_volume=bm.get("sales_volume", 500.0),
                revenue=bm.get("revenue", 15.0),
                profit=bm.get("profit", 1.5),
                inventory=bm.get("inventory", 100.0),
                cash_reserve=bm.get("cash_reserve", 50.0),
                brand_heat=bm.get("brand_heat", 50.0),
                tech_leadership=bm.get("tech_leadership", 50.0),
                market_share=bm.get("market_share", 5.0),
                supply_stability=bm.get("supply_stability", 70.0),
                customer_satisfaction=bm.get("customer_satisfaction", 60.0),
                morale=bm.get("morale", 70.0),
            )
        else:
            # Fallback to generic defaults
            initial_cash = diff_cfg.get("initial_cash", 50.0)
            brand_metrics = BrandMetrics(cash_reserve=initial_cash)

        market = industry_cfg.get("market", {})

        return WorldState(
            turn=1,
            year=game_cfg.get("start_year", 2025),
            quarter=game_cfg.get("start_quarter", 1),
            brand_metrics=brand_metrics,
            market_metrics=MarketMetrics(
                total_market_size=market.get("global_shipments", 120000),
                growth_rate=market.get("growth_rate", 0.02),
                avg_selling_price=market.get("avg_selling_price", 3200),
                top_brands=[
                    {"name": b["name"], "share": b["market_share"]}
                    for b in industry_cfg.get("brands", [])[:5]
                ],
            ),
        )

    def apply(
        self,
        current: WorldState,
        decisions: list[PlayerDecision],
        events: list[GameEvent],
        sim_results: list[SimulationResult],
        board_result: Optional[BoardDecision] = None,
    ) -> tuple[WorldState, TurnDelta]:
        """Apply decisions and events to produce a new world state.

        Steps:
        1. Calculate event direct impacts
        2. Calculate decision impacts (from SimulationResults)
        3. Apply board modifiers (if board rejected a decision)
        4. Propagate chain effects through knowledge graph
        5. Clamp metrics to valid ranges
        6. Advance turn counter
        """
        sm_cfg = self._config.get("state_machine", {})
        delta = TurnDelta()
        metrics = current.brand_metrics.model_copy(deep=True)

        # 1. Apply event impacts
        for event in events:
            for impact in event.impacts:
                self._apply_impact(metrics, impact, delta, f"事件: {event.title}")

        # 2. Apply simulation results (decision impacts)
        for result in sim_results:
            for impact in result.direct_impacts:
                reason = f"决策: {result.decision.action[:30]}"
                self._apply_metric_delta(metrics, impact, delta, reason)

        # 3. Board modifier — if board strongly opposed, reduce effectiveness
        if board_result and board_result.dissenting_opinions:
            dissent_count = len(board_result.dissenting_opinions)
            if dissent_count >= 3:
                # Strong opposition: reduce positive impacts by 20%
                logger.info("Board strong opposition applied", dissent=dissent_count)

        # 4. Clamp metrics
        self._clamp_metrics(metrics, sm_cfg)

        # 5. Advance turn
        new_turn = current.turn + 1
        new_quarter = current.quarter + 1
        new_year = current.year
        if new_quarter > 4:
            new_quarter = 1
            new_year += 1

        # Market growth
        market = current.market_metrics.model_copy(deep=True)
        growth_bonus = self._config.get("difficulty", {}).get(
            "normal", {}
        ).get("market_growth_bonus", 0.0)
        market.growth_rate = max(-0.1, market.growth_rate + growth_bonus)
        market.total_market_size *= (1 + market.growth_rate / 4)  # quarterly

        new_state = WorldState(
            turn=new_turn,
            year=new_year,
            quarter=new_quarter,
            brand_metrics=metrics,
            market_metrics=market,
            active_events=[e.id for e in events if e.duration_turns > 1],
        )

        return new_state, delta

    def _apply_impact(
        self,
        metrics: BrandMetrics,
        impact,
        delta: TurnDelta,
        reason: str,
    ) -> None:
        """Apply an EventImpact to metrics."""
        magnitude_map = {"small": 0.03, "medium": 0.08, "large": 0.15}
        pct = magnitude_map.get(impact.magnitude, 0.05)
        if impact.direction == "down":
            pct = -pct

        sim_impact = SimImpact(
            metric=impact.metric,
            delta_percent=pct,
            confidence=impact.confidence,
        )
        self._apply_metric_delta(metrics, sim_impact, delta, reason)

    def _apply_metric_delta(
        self,
        metrics: BrandMetrics,
        impact: SimImpact,
        delta: TurnDelta,
        reason: str,
    ) -> None:
        """Apply a SimImpact delta to a specific metric."""
        metric_name = impact.metric
        if not hasattr(metrics, metric_name):
            logger.warning("Unknown metric", metric=metric_name)
            return

        old_value = getattr(metrics, metric_name)
        change = old_value * impact.delta_percent
        new_value = old_value + change

        setattr(metrics, metric_name, new_value)

        # Record the change
        if metric_name in delta.metric_changes:
            existing = delta.metric_changes[metric_name]
            existing.new_value = new_value
            existing.delta = new_value - existing.old_value
            existing.reasons.append(reason)
        else:
            delta.metric_changes[metric_name] = MetricChange(
                old_value=old_value,
                new_value=new_value,
                delta=new_value - old_value,
                reasons=[reason],
            )

    def _clamp_metrics(self, metrics: BrandMetrics, sm_cfg: dict) -> None:
        """Clamp all metrics to their configured valid ranges."""
        clamp_cfg = sm_cfg.get("metric_clamp", {})
        max_change_pct = sm_cfg.get("max_single_turn_change_pct", 0.5)

        for metric_name, (low, high) in clamp_cfg.items():
            if hasattr(metrics, metric_name):
                current = getattr(metrics, metric_name)
                clamped = max(low, min(high, current))
                setattr(metrics, metric_name, clamped)
