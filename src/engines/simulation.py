"""AI simulation engine — LLM-driven decision impact analysis."""

from typing import TYPE_CHECKING, Optional

from src.engines.knowledge_graph import KnowledgeGraph
from src.llm.client import LLMClient
from src.schemas.intel import GameEvent
from src.schemas.simulation import (
    ChainEffect,
    PlayerDecision,
    QualitativeFeedback,
    SimImpact,
    SimulationResult,
)
from src.schemas.world import WorldState
from src.utils.config import load_yaml
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.engines.rss_intel import RSSIntelEngine
    from src.services.rss_service import RSSService


from pydantic import BaseModel, Field


class SimulationLLMOutput(BaseModel):
    """Expected JSON structure from LLM simulation response."""
    direct_impacts: list[SimImpact] = []
    qualitative_feedbacks: list[QualitativeFeedback] = []
    chain_effects: list[ChainEffect] = []
    narrative: str = ""
    risk_warnings: list[str] = []


class SimulationEngine:
    """AI-driven simulation engine.

    Uses LLM + knowledge graph to reason about decision impacts.
    Falls back to rule-based estimation when LLM is unavailable.
    """

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        kg: Optional[KnowledgeGraph] = None,
        rss_service: Optional["RSSService"] = None,
        rss_intel_engine: Optional["RSSIntelEngine"] = None,
    ):
        self.llm = llm
        self.kg = kg
        self.rss_service = rss_service
        self.rss_intel_engine = rss_intel_engine
        self._prompts = load_yaml("prompts.yaml")
        self._game_config = load_yaml("game.yaml")

    async def _build_rss_context(self, decision: PlayerDecision) -> str:
        """Build RSS intelligence context relevant to the decision category.

        Returns a formatted string summarising RSS signals and trend adjustments.
        Falls back to empty string when RSS is unavailable.
        """
        if not self.rss_service or not self.rss_intel_engine:
            return "（RSS情报不可用）"

        # Get cached RSS items or fetch fresh
        items = self.rss_service.get_cached()
        if not items:
            try:
                items = await self.rss_service.fetch_all()
            except Exception as e:
                logger.warning("RSS fetch failed for simulation context", error=str(e))
                return "（RSS情报获取失败）"

        if not items:
            return "（暂无RSS情报）"

        signals = self.rss_intel_engine.analyze_items(items)
        if not signals:
            return "（RSS情报分析无结果）"

        # Map decision category to relevant RSS game types
        category_map = {
            "rd": ["technology"],
            "marketing": ["market"],
            "supply": ["supply_chain"],
            "product": ["technology", "market"],
            "finance": ["market", "supply_chain"],
            "hr": ["market", "technology", "supply_chain"],
        }
        relevant_types = category_map.get(decision.category.value, [])

        # Filter signals relevant to this decision category
        if relevant_types:
            relevant = [s for s in signals if s.game_type in relevant_types]
        else:
            relevant = signals

        if not relevant:
            relevant = signals[:5]

        # Build summary text
        lines: list[str] = []
        lines.append(f"RSS情报摘要（共{len(relevant)}条相关信号）：")

        # Top 5 key events
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        top = sorted(relevant, key=lambda s: severity_order.get(s.severity, 4))[:5]
        for sig in top:
            lines.append(
                f"  - [{sig.severity.upper()}] {sig.title} "
                f"(来源:{sig.source}, 情感:{sig.sentiment})"
            )
            if sig.tech_tags:
                lines.append(f"    技术标签: {', '.join(sig.tech_tags[:3])}")

        # Trend adjustments
        # Use default trend weights of 1.0 for all tags
        default_trends = {tag: 1.0 for sig in relevant for tag in sig.tech_tags}
        adjustments = self.rss_intel_engine.calculate_trend_adjustments(
            relevant, default_trends
        )
        if adjustments:
            lines.append("\n趋势调整建议：")
            for adj in adjustments[:3]:
                lines.append(
                    f"  - {adj.tag}: {adj.current_weight}→{adj.adjusted_weight} "
                    f"({adj.reason})"
                )

        # Sentiment summary
        pos = sum(1 for s in relevant if s.sentiment == "positive")
        neg = sum(1 for s in relevant if s.sentiment == "negative")
        neu = sum(1 for s in relevant if s.sentiment == "neutral")
        lines.append(f"\n情感分布: 正面{pos} / 负面{neg} / 中性{neu}")

        return "\n".join(lines)

    async def simulate(
        self,
        decision: PlayerDecision,
        state: WorldState,
        active_events: list[GameEvent],
    ) -> SimulationResult:
        """Simulate the impact of a single decision.

        If LLM is available, uses it for reasoning.
        Otherwise falls back to rule-based estimation.
        """
        if self.llm:
            try:
                return await self._simulate_with_llm(decision, state, active_events)
            except Exception as e:
                logger.error("LLM simulation failed, falling back", error=str(e))

        return self._simulate_fallback(decision, state)

    async def _simulate_with_llm(
        self,
        decision: PlayerDecision,
        state: WorldState,
        active_events: list[GameEvent],
    ) -> SimulationResult:
        """Use LLM for intelligent decision simulation."""
        prompts = self._prompts.get("simulation", {})
        system_prompt = prompts.get("system", "你是手机产业分析师。")
        user_template = prompts.get("user", "")

        # Build context
        brand = state.brand_metrics
        metrics_summary = (
            f"资金: {brand.cash_reserve:.1f}亿元 | 市场份额: {brand.market_share:.1f}%\n"
            f"品牌热度: {brand.brand_heat:.0f} | 技术领先: {brand.tech_leadership:.0f}\n"
            f"供应链稳定: {brand.supply_stability:.0f} | 客户满意度: {brand.customer_satisfaction:.0f}\n"
            f"销量: {brand.sales_volume:.0f}万台 | 营收: {brand.revenue:.1f}亿元"
        )

        events_summary = "\n".join(f"- {e.title}: {e.description}" for e in active_events[:5])
        if not events_summary:
            events_summary = "（无当前生效事件）"

        kg_context = ""
        if self.kg:
            kg_context = self.kg.get_related_context(decision.category.value, max_entities=8)

        # Build RSS intelligence context
        rss_intel_summary = await self._build_rss_context(decision)

        user_prompt = user_template.format(
            year=state.year,
            quarter=state.quarter,
            turn=state.turn,
            brand_metrics_summary=metrics_summary,
            active_events_summary=events_summary,
            knowledge_context=kg_context or "（无相关知识图谱数据）",
            rss_intel_summary=rss_intel_summary,
            decision_category=decision.category.value,
            decision_action=decision.action,
            decision_budget=f"{decision.budget:.1f}亿元" if decision.budget else "未指定",
        )

        output = await self.llm.chat_json(
            "simulation", system_prompt, user_prompt, SimulationLLMOutput
        )

        # Validate and clamp
        result = SimulationResult(
            turn=state.turn,
            decision=decision,
            direct_impacts=self._clamp_impacts(output.direct_impacts),
            qualitative_feedbacks=output.qualitative_feedbacks,
            chain_effects=output.chain_effects,
            narrative=output.narrative,
            risk_warnings=output.risk_warnings,
        )

        return result

    def _simulate_fallback(
        self,
        decision: PlayerDecision,
        state: WorldState,
    ) -> SimulationResult:
        """Rule-based fallback when LLM is unavailable."""
        impacts = []
        feedbacks = []
        warnings = []

        # Simple heuristic mapping
        category = decision.category
        budget_factor = min(1.0, (decision.budget or 5.0) / 20.0)

        if category.value == "rd":
            impacts.append(SimImpact(metric="tech_leadership", delta_percent=0.05 * budget_factor, confidence=0.6, reasoning="研发投入提升技术领先度"))
            impacts.append(SimImpact(metric="cash_reserve", delta_percent=-0.03 * budget_factor, confidence=0.8, reasoning="研发消耗资金"))
            feedbacks.append(QualitativeFeedback(source="研发团队", reaction="团队对新技术方向感到兴奋", sentiment="positive"))
        elif category.value == "marketing":
            impacts.append(SimImpact(metric="brand_heat", delta_percent=0.06 * budget_factor, confidence=0.6, reasoning="营销投入提升品牌热度"))
            impacts.append(SimImpact(metric="cash_reserve", delta_percent=-0.04 * budget_factor, confidence=0.8, reasoning="营销消耗资金"))
        elif category.value == "supply":
            impacts.append(SimImpact(metric="supply_stability", delta_percent=0.05 * budget_factor, confidence=0.7, reasoning="供应链优化提升稳定性"))
            impacts.append(SimImpact(metric="cash_reserve", delta_percent=-0.02 * budget_factor, confidence=0.8, reasoning="供应链投入消耗资金"))
        elif category.value == "product":
            impacts.append(SimImpact(metric="customer_satisfaction", delta_percent=0.04 * budget_factor, confidence=0.5, reasoning="产品改善提升满意度"))
            impacts.append(SimImpact(metric="sales_volume", delta_percent=0.03 * budget_factor, confidence=0.5, reasoning="产品改善带动销量"))
            impacts.append(SimImpact(metric="cash_reserve", delta_percent=-0.03 * budget_factor, confidence=0.8, reasoning="产品投入消耗资金"))
        elif category.value == "finance":
            impacts.append(SimImpact(metric="cash_reserve", delta_percent=0.05, confidence=0.7, reasoning="财务优化提升资金储备"))
        elif category.value == "hr":
            impacts.append(SimImpact(metric="morale", delta_percent=0.05 * budget_factor, confidence=0.6, reasoning="人事投入提升团队士气"))
            impacts.append(SimImpact(metric="cash_reserve", delta_percent=-0.02 * budget_factor, confidence=0.8, reasoning="人事投入消耗资金"))

        warnings.append("此为简化推演，未考虑市场动态和竞品反应")

        return SimulationResult(
            turn=state.turn,
            decision=decision,
            direct_impacts=impacts,
            qualitative_feedbacks=feedbacks,
            chain_effects=[],
            narrative=f"公司执行了{decision.category.value}方向的决策：{decision.action}",
            risk_warnings=warnings,
        )

    def _clamp_impacts(self, impacts: list[SimImpact]) -> list[SimImpact]:
        """Clamp impact percentages to reasonable ranges."""
        max_pct = self._game_config.get("state_machine", {}).get(
            "max_single_turn_change_pct", 0.5
        )
        clamped = []
        for impact in impacts:
            new_impact = impact.model_copy()
            new_impact.delta_percent = max(-max_pct, min(max_pct, new_impact.delta_percent))
            clamped.append(new_impact)
        return clamped
