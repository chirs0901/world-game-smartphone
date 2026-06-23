"""Event generation system — RSS-driven + preset event pool fallback.

Architecture:
    1. Primary: RSS industry news → RSSIntelEngine → game events (real-time)
    2. Fallback: Static JSON event pool → random selection (offline/testing)
    3. Hybrid: Mix of RSS events + static events (default 60/40 ratio)
"""

import json
import random
import uuid
from typing import TYPE_CHECKING, Optional

from src.engines.knowledge_graph import KnowledgeGraph
from src.llm.client import LLMClient
from src.schemas.intel import EventImpact, EventSeverity, GameEvent, NewsCategory
from src.schemas.world import WorldState
from src.utils.config import get_data_dir, load_yaml
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.engines.rss_intel import RSSIntelEngine
    from src.services.rss_service import RSSService


# Predefined events for when LLM is unavailable
_FALLBACK_EVENTS = [
    GameEvent(
        title="芯片价格上涨",
        description="全球芯片供应链紧张，SoC采购成本上涨约10%。",
        category=NewsCategory.SUPPLY_CHAIN,
        severity=EventSeverity.MEDIUM,
        impacts=[EventImpact(metric="cash_reserve", direction="down", magnitude="medium", confidence=0.8)],
        response_options=["提前锁定库存", "寻找替代供应商", "接受涨价并调整定价"],
        duration_turns=2,
    ),
    GameEvent(
        title="竞品发布旗舰新机",
        description="主要竞争对手发布了搭载最新技术的旗舰手机，市场反响热烈。",
        category=NewsCategory.COMPETITOR,
        severity=EventSeverity.MEDIUM,
        impacts=[EventImpact(metric="market_share", direction="down", magnitude="small", confidence=0.7)],
        response_options=["加速自家旗舰发布", "加大营销投入", "聚焦差异化功能"],
        duration_turns=1,
    ),
    GameEvent(
        title="5G渗透率突破新高",
        description="全球5G手机渗透率突破70%，消费者换机需求向5G机型集中。",
        category=NewsCategory.TECHNOLOGY,
        severity=EventSeverity.LOW,
        impacts=[EventImpact(metric="tech_leadership", direction="up", magnitude="small", confidence=0.6)],
        response_options=["加大5G产品线", "投入6G预研", "维持现状"],
        duration_turns=1,
    ),
    GameEvent(
        title="折叠屏出货量翻倍",
        description="折叠屏手机出货量同比增长100%，但良率问题仍然存在。",
        category=NewsCategory.TECHNOLOGY,
        severity=EventSeverity.MEDIUM,
        impacts=[
            EventImpact(metric="brand_heat", direction="up", magnitude="small", confidence=0.5),
            EventImpact(metric="tech_leadership", direction="up", magnitude="small", confidence=0.6),
        ],
        response_options=["启动折叠屏项目", "观望等待技术成熟", "与面板厂商深度合作"],
        duration_turns=2,
    ),
    GameEvent(
        title="东南亚市场需求激增",
        description="东南亚智能手机市场同比增长15%，中低端机型需求旺盛。",
        category=NewsCategory.MARKET,
        severity=EventSeverity.LOW,
        impacts=[EventImpact(metric="sales_volume", direction="up", magnitude="medium", confidence=0.7)],
        response_options=["加大东南亚渠道投入", "推出区域定制机型", "维持现有市场策略"],
        duration_turns=1,
    ),
]


class EventGenerator:
    """Event generation system for the game world.

    Primary mode: RSS-driven hybrid (60% RSS + 40% static).
    Fallback: Static event pool when RSS is unavailable.
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
        self._event_pool: list[GameEvent] = []
        self._load_event_pool()

    def _load_event_pool(self) -> None:
        """Load preset events from JSON files."""
        events_dir = get_data_dir() / "events"
        if events_dir.exists():
            for json_file in sorted(events_dir.glob("*.json")):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for item in data:
                        event = GameEvent(
                            id=item.get("id", str(uuid.uuid4())),
                            title=item["title"],
                            description=item["description"],
                            category=NewsCategory(item.get("category", "market")),
                            severity=EventSeverity(item.get("severity", "medium")),
                            impacts=[EventImpact(**i) for i in item.get("impacts", [])],
                            response_options=item.get("response_options", []),
                            chain_effects=item.get("chain_effects", []),
                            duration_turns=item.get("duration_turns", 1),
                        )
                        self._event_pool.append(event)
                    logger.info("Loaded event file", file=json_file.name, count=len(data))
                except Exception as e:
                    logger.error("Failed to load event file", file=json_file.name, error=str(e))

        # Add fallback events if pool is empty
        if not self._event_pool:
            self._event_pool = [e.model_copy() for e in _FALLBACK_EVENTS]
            for e in self._event_pool:
                e.id = str(uuid.uuid4())
            logger.info("Using fallback events", count=len(self._event_pool))

    async def roll_events_rss(
        self,
        state: WorldState,
        difficulty: str = "normal",
        excluded_ids: Optional[set[str]] = None,
        rss_ratio: float = 0.6,
    ) -> list[GameEvent]:
        """Generate events using hybrid RSS + static mode.

        Args:
            state: Current world state
            difficulty: Game difficulty level
            excluded_ids: Event IDs already used
            rss_ratio: Fraction of events from RSS (0.0=static only, 1.0=RSS only)

        Returns:
            List of GameEvents for this turn
        """
        diff_cfg = load_yaml("game.yaml").get("difficulty", {}).get(difficulty, {})
        event_range = diff_cfg.get("events_per_turn", [2, 3])
        total_count = random.randint(event_range[0], event_range[1])

        rss_count = round(total_count * rss_ratio)
        static_count = total_count - rss_count

        # Try to get RSS events
        rss_events: list[GameEvent] = []
        if rss_count > 0:
            rss_events = await self._generate_rss_events(state, rss_count)
            # If RSS returned fewer than requested, fill gap with static
            if len(rss_events) < rss_count:
                static_count += rss_count - len(rss_events)

        # Get static events for the remainder
        static_events = self._roll_static_events(state, difficulty, static_count, excluded_ids)

        result = rss_events + static_events
        random.shuffle(result)
        return result

    async def _generate_rss_events(
        self,
        state: WorldState,
        count: int,
    ) -> list[GameEvent]:
        """Generate GameEvents from RSS intelligence signals."""
        if not self.rss_service or not self.rss_intel_engine:
            return []

        # Get cached RSS items, or fetch if cache is empty
        items = self.rss_service.get_cached()
        if not items:
            try:
                items = await self.rss_service.fetch_all()
            except Exception as e:
                logger.warning("RSS fetch failed, falling back to static", error=str(e))
                return []

        if not items:
            return []

        # Analyze RSS items and generate game event drafts
        signals = self.rss_intel_engine.analyze_items(items)
        drafts = self.rss_intel_engine.generate_game_events(signals)

        if not drafts:
            return []

        # Convert GameEventDraft → GameEvent
        events: list[GameEvent] = []
        for draft in drafts:
            # Parse magnitude from hint like "+2~5" → "medium"
            magnitude_map = {"small": "small", "medium": "medium", "large": "large"}
            impacts: list[EventImpact] = []
            for imp in draft.impacts:
                hint = imp.get("magnitude_hint", "medium")
                # Extract first number from hint like "+2~5"
                try:
                    num_str = hint.lstrip("+-").split("~")[0].split("-")[0].strip()
                    num = float(num_str) if num_str else 3.0
                except (ValueError, IndexError):
                    num = 3.0
                if num <= 2:
                    mag = "small"
                elif num <= 5:
                    mag = "medium"
                else:
                    mag = "large"

                impacts.append(EventImpact(
                    metric=imp["metric"],
                    direction=imp["direction"],
                    magnitude=mag,
                    confidence=0.6,
                ))

            event = GameEvent(
                id=str(uuid.uuid4()),
                turn=state.turn,
                title=draft.title,
                description=draft.description,
                category=NewsCategory(draft.category) if draft.category in [
                    "market", "technology", "supply_chain", "policy", "competitor", "consumer"
                ] else NewsCategory.MARKET,
                severity=EventSeverity(draft.severity),
                impacts=impacts,
                response_options=draft.response_options,
                duration_turns=2 if draft.severity in ("high", "critical") else 1,
                source_rss=draft.source_rss,
                source_link=draft.source_link,
                component_id=draft.component_id,
                tech_tags=draft.tech_tags,
                sentiment=draft.sentiment,
                rss_driven=True,
            )
            events.append(event)

        # Weighted sampling by severity
        if len(events) > count:
            weights = []
            for e in events:
                if e.severity == EventSeverity.CRITICAL:
                    weights.append(0.15)
                elif e.severity == EventSeverity.HIGH:
                    weights.append(0.35)
                elif e.severity == EventSeverity.MEDIUM:
                    weights.append(0.5)
                else:
                    weights.append(0.8)

            selected: list[GameEvent] = []
            pool = list(events)
            pool_weights = list(weights)
            for _ in range(count):
                if not pool:
                    break
                chosen = random.choices(pool, weights=pool_weights, k=1)[0]
                idx = pool.index(chosen)
                selected.append(chosen)
                pool.pop(idx)
                pool_weights.pop(idx)
            return selected

        return events

    def _roll_static_events(
        self,
        state: WorldState,
        difficulty: str,
        count: int,
        excluded_ids: Optional[set[str]] = None,
    ) -> list[GameEvent]:
        """Roll events from the static event pool (original logic)."""
        diff_cfg = load_yaml("game.yaml").get("difficulty", {}).get(difficulty, {})
        num_events = count

        # Filter available events
        excluded = excluded_ids or set()
        available = [e for e in self._event_pool if e.id not in excluded]

        if not available:
            # Reset pool if all events have been used
            available = [e.model_copy() for e in self._event_pool]
            for e in available:
                e.id = str(uuid.uuid4())

        # Weight by severity (critical events are rarer)
        severity_bias = diff_cfg.get("event_severity_bias", 0.5)
        weights = []
        for e in available:
            if e.severity == EventSeverity.CRITICAL:
                weights.append(0.1 * severity_bias)
            elif e.severity == EventSeverity.HIGH:
                weights.append(0.3 * severity_bias)
            elif e.severity == EventSeverity.MEDIUM:
                weights.append(0.5)
            else:
                weights.append(0.8)

        # Sample events WITHOUT duplicates
        num_events = min(num_events, len(available))
        selected = []
        pool = list(available)
        pool_weights = list(weights)
        for _ in range(num_events):
            if not pool:
                break
            chosen = random.choices(pool, weights=pool_weights, k=1)[0]
            idx = pool.index(chosen)
            selected.append(chosen)
            pool.pop(idx)
            pool_weights.pop(idx)

        # Assign fresh IDs and current turn
        result = []
        for event in selected:
            new_event = event.model_copy(deep=True)
            new_event.id = str(uuid.uuid4())
            new_event.turn = state.turn
            result.append(new_event)

        return result

    def roll_events(
        self,
        state: WorldState,
        difficulty: str = "normal",
        excluded_ids: Optional[set[str]] = None,
    ) -> list[GameEvent]:
        """Generate events from static pool (synchronous, for backward compatibility)."""
        diff_cfg = load_yaml("game.yaml").get("difficulty", {}).get(difficulty, {})
        event_range = diff_cfg.get("events_per_turn", [2, 3])
        num_events = random.randint(event_range[0], event_range[1])
        return self._roll_static_events(state, difficulty, num_events, excluded_ids)

    def generate_news_for_events(self, events: list[GameEvent], state: WorldState) -> list[dict]:
        """Generate news items for the given events.

        Returns simplified news dicts suitable for the intel center.
        """
        news = []
        for event in events:
            source = "RSS产业情报" if event.rss_driven else "产业情报"
            sentiment = event.sentiment or (
                "negative" if any(i.direction == "down" for i in event.impacts) else "neutral"
            )
            tags = event.tech_tags if event.tech_tags else [event.category.value]
            news.append({
                "id": str(uuid.uuid4()),
                "turn": state.turn,
                "category": event.category.value,
                "headline": event.title,
                "content": event.description,
                "source": source,
                "source_link": event.source_link,
                "sentiment": sentiment,
                "is_critical": event.severity in (EventSeverity.HIGH, EventSeverity.CRITICAL),
                "tags": tags,
            })
        return news
