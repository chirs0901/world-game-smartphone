"""RSS Intelligence Adapter — bridges real-time RSS feeds to game mechanics.

Converts industry news into:
1. Game events (market/tech/supply/policy)
2. Debate topics for AI board meetings
3. Tech roadmap trend weight adjustments
4. Market intelligence summaries for sandbox simulation

This is the "real-world data → game content" pipeline.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.services.rss_service import RSSItem


# ──────────────────────────────────────────────────────────
# Category → Game Component Mapping
# ──────────────────────────────────────────────────────────

CATEGORY_TO_GAME_TYPE = {
    "手机品牌动态": "market",
    "屏幕显示": "technology",
    "平台芯片": "technology",
    "影像": "technology",
    "散热": "technology",
    "电池": "technology",
    "存储供应": "supply_chain",
    "AI": "technology",
}

CATEGORY_TO_COMPONENT_ID = {
    "屏幕显示": "display",
    "平台芯片": "soc",
    "影像": "camera",
    "散热": "cooling",
    "电池": "battery",
    "存储供应": "storage",
    "AI": "ai_npu",
}

# Keyword → Tech selling-point tag mapping
KEYWORD_TO_TAG: dict[str, str] = {
    "折叠屏": "折叠屏", "折叠": "折叠屏", "foldable": "折叠屏", "UTG": "UTG超薄玻璃",
    "3nm": "3nm旗舰", "2nm": "自研2nm", "自研芯片": "自研芯片", "自研": "自研芯片",
    "RISC-V": "RISC-V",
    "卫星通信": "卫星通信", "卫星": "卫星通信",
    "固态电池": "固态电池", "硅碳": "硅碳负极", "硅碳负极": "硅碳负极",
    "120W": "120W极速闪充", "快充": "120W极速闪充",
    "潜望": "潜望长焦", "长焦": "潜望长焦", "连续变焦": "连续光变", "光变": "连续光变",
    "大模型": "端侧大模型", "Agent": "Agent智能体", "NPU": "独立AI引擎",
    "LTPO": "LTPO自适应刷新", "OLED": "高亮度",
    "VC": "VC液冷", "均热板": "VC液冷", "主动散热": "主动散热",
    "LPDDR5X": "LPDDR5X", "LPDDR6": "LPDDR6", "UFS4": "UFS4.1", "UFS5": "带宽翻倍",
    "5G-A": "5G-A", "5.5G": "5G-A", "WiFi7": "WiFi7", "WiFi 7": "WiFi7",
    "1英寸": "1英寸大底", "IMX989": "1英寸大底", "计算摄影": "计算摄影",
}

# Sentiment keywords for intelligence analysis
POSITIVE_KEYWORDS = [
    "突破", "领先", "量产", "成功", "首发", "提升", "创新", "增长",
    "降低成本", "良率提升", "出货量增长", "市场份额提升", "获批", "认证",
    "合作", "签约", "投资", "融资", "发布", "上市", "开售", "破纪录",
]

NEGATIVE_KEYWORDS = [
    "短缺", "延迟", "良率低", "问题", "召回", "下降", "亏损", "裁员",
    "停工", "涨价", "断供", "危机", "下滑", "疲软", "库存积压", "砍单",
    "退场", "退出", "失败", "诉讼", "禁令", "制裁", "限制",
]

# Severity scoring rules
SEVERITY_HIGH_KEYWORDS = ["断供", "制裁", "禁令", "召回", "危机", "停产", "破产", "退场"]
SEVERITY_CRITICAL_KEYWORDS = ["战争", "地震", "爆炸", "封锁", "全面制裁"]


@dataclass
class IntelSignal:
    """A market intelligence signal extracted from RSS feeds."""
    source: str
    category: str
    title: str
    description: str
    link: str
    published: str
    game_type: str  # "market" / "technology" / "supply_chain" / "policy"
    component_id: Optional[str]  # which component category this affects
    tech_tags: list[str]  # matched tech selling-point tags
    sentiment: str  # "positive" / "negative" / "neutral"
    sentiment_score: float  # -1.0 to 1.0
    severity: str  # "low" / "medium" / "high" / "critical"
    impact_hint: str  # human-readable impact description


@dataclass
class GameEventDraft:
    """A game event generated from RSS intelligence."""
    title: str
    description: str
    category: str  # "market" / "technology" / "supply_chain" / "policy" / "competitor"
    severity: str  # "low" / "medium" / "high" / "critical"
    source_rss: str  # original RSS source name
    source_link: str  # original article link
    component_id: Optional[str]  # affected component
    tech_tags: list[str]
    sentiment: str
    impacts: list[dict]  # [{metric, direction, magnitude_hint}]
    response_options: list[str]
    rss_driven: bool = True


@dataclass
class DebateTopicDraft:
    """A debate topic for AI board meeting, generated from RSS intelligence."""
    topic: str
    context: str  # background from RSS article
    source_link: str
    category: str  # RSS category
    component_id: Optional[str]
    tech_tags: list[str]
    sentiment: str
    suggested_positions: list[str]  # suggested stance options for board members


@dataclass
class TrendAdjustment:
    """A trend weight adjustment derived from RSS intelligence."""
    tag: str  # tech selling-point tag
    current_weight: float  # current weight in MARKET_TRENDS
    adjusted_weight: float  # new weight after RSS influence
    reason: str  # why the adjustment
    signal_count: int  # how many RSS items triggered this


@dataclass
class MarketIntelSummary:
    """Summary of market intelligence for the sandbox simulation."""
    total_signals: int
    positive_count: int
    negative_count: int
    neutral_count: int
    top_tags: list[tuple[str, int]]  # (tag, signal_count) sorted by frequency
    category_breakdown: dict[str, int]  # category → signal count
    key_events: list[str]  # top event titles
    trend_adjustments: list[TrendAdjustment]
    generated_at: str


class RSSIntelEngine:
    """Analyzes RSS items and generates game-relevant intelligence."""

    def __init__(self):
        self._keyword_to_tag = KEYWORD_TO_TAG
        self._positive = POSITIVE_KEYWORDS
        self._negative = NEGATIVE_KEYWORDS

    def analyze_item(self, item: RSSItem) -> IntelSignal:
        """Analyze a single RSS item and extract intelligence signals."""
        text = f"{item.title} {item.description}"

        # Extract tech tags
        tech_tags: list[str] = []
        for keyword, tag in self._keyword_to_tag.items():
            if keyword.lower() in text.lower() and tag not in tech_tags:
                tech_tags.append(tag)

        # Sentiment analysis
        pos_count = sum(1 for kw in self._positive if kw in text)
        neg_count = sum(1 for kw in self._negative if kw in text)

        if pos_count > neg_count:
            sentiment = "positive"
            sentiment_score = min(1.0, (pos_count - neg_count) * 0.3)
        elif neg_count > pos_count:
            sentiment = "negative"
            sentiment_score = max(-1.0, -(neg_count - pos_count) * 0.3)
        else:
            sentiment = "neutral"
            sentiment_score = 0.0

        # Severity assessment
        severity = "low"
        if any(kw in text for kw in SEVERITY_CRITICAL_KEYWORDS):
            severity = "critical"
        elif any(kw in text for kw in SEVERITY_HIGH_KEYWORDS):
            severity = "high"
        elif sentiment_score < -0.5 or neg_count >= 2:
            severity = "medium"

        # Determine game type and component
        game_type = CATEGORY_TO_GAME_TYPE.get(item.source_category, "market")
        component_id = CATEGORY_TO_COMPONENT_ID.get(item.source_category)

        # Impact hint
        if tech_tags:
            impact_hint = f"影响器件: {', '.join(tech_tags[:3])}"
        elif game_type == "market":
            impact_hint = "影响市场份额与品牌热度"
        elif game_type == "supply_chain":
            impact_hint = "影响供应链稳定性"
        else:
            impact_hint = "影响技术领先度"

        return IntelSignal(
            source=item.source_name,
            category=item.source_category,
            title=item.title,
            description=item.description,
            link=item.link,
            published=item.published,
            game_type=game_type,
            component_id=component_id,
            tech_tags=tech_tags,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            severity=severity,
            impact_hint=impact_hint,
        )

    def analyze_items(self, items: list[RSSItem]) -> list[IntelSignal]:
        """Analyze a batch of RSS items."""
        return [self.analyze_item(item) for item in items]

    def generate_game_events(self, signals: list[IntelSignal]) -> list[GameEventDraft]:
        """Generate game events from intelligence signals.

        Only significant signals (medium+ severity or with tech tags) become events.
        """
        events: list[GameEventDraft] = []
        seen_titles: set[str] = set()

        for sig in signals:
            # Skip low-severity items without tech tags
            if sig.severity == "low" and not sig.tech_tags:
                continue

            # Deduplicate by title
            title_key = sig.title[:50].lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            # Build impact list
            impacts: list[dict] = []
            if sig.sentiment == "positive":
                if sig.game_type == "technology":
                    impacts.append({"metric": "tech_leadership", "direction": "up", "magnitude_hint": "+2~5"})
                    impacts.append({"metric": "brand_heat", "direction": "up", "magnitude_hint": "+1~3"})
                elif sig.game_type == "market":
                    impacts.append({"metric": "market_share", "direction": "up", "magnitude_hint": "+0.5~2"})
                    impacts.append({"metric": "brand_heat", "direction": "up", "magnitude_hint": "+1~3"})
                elif sig.game_type == "supply_chain":
                    impacts.append({"metric": "supply_stability", "direction": "up", "magnitude_hint": "+2~5"})
            elif sig.sentiment == "negative":
                if sig.game_type == "technology":
                    impacts.append({"metric": "tech_leadership", "direction": "down", "magnitude_hint": "-1~3"})
                elif sig.game_type == "market":
                    impacts.append({"metric": "market_share", "direction": "down", "magnitude_hint": "-0.5~2"})
                    impacts.append({"metric": "brand_heat", "direction": "down", "magnitude_hint": "-1~3"})
                elif sig.game_type == "supply_chain":
                    impacts.append({"metric": "supply_stability", "direction": "down", "magnitude_hint": "-2~5"})

            # Build response options
            response_options: list[str] = []
            if sig.sentiment == "positive":
                response_options.append("加大相关技术投入，抢占先机")
                response_options.append("与该供应商建立战略合作")
                response_options.append("观望，暂不行动")
            elif sig.sentiment == "negative":
                response_options.append("启动应急预案，寻找替代供应商")
                response_options.append("调整产品路线图，规避风险")
                response_options.append("保持现有策略，承受短期影响")

            events.append(GameEventDraft(
                title=sig.title,
                description=sig.description or sig.impact_hint,
                category=sig.game_type if sig.game_type != "supply_chain" else "supply_chain",
                severity=sig.severity,
                source_rss=sig.source,
                source_link=sig.link,
                component_id=sig.component_id,
                tech_tags=sig.tech_tags,
                sentiment=sig.sentiment,
                impacts=impacts,
                response_options=response_options,
            ))

        return events

    def generate_debate_topics(self, signals: list[IntelSignal]) -> list[DebateTopicDraft]:
        """Generate debate topics for AI board meetings from RSS signals."""
        topics: list[DebateTopicDraft] = []
        seen: set[str] = set()

        for sig in signals:
            if not sig.tech_tags and sig.severity == "low":
                continue

            topic_key = frozenset(sig.tech_tags) if sig.tech_tags else sig.title[:30]
            if topic_key in seen:
                continue
            seen.add(topic_key)

            # Build topic title
            if sig.tech_tags:
                topic = f"关于「{'、'.join(sig.tech_tags[:3])}」的技术路线抉择"
            elif sig.game_type == "market":
                topic = f"市场动态：{sig.title[:40]}"
            else:
                topic = sig.title[:50]

            # Suggested positions for board members
            positions: list[str] = []
            if sig.sentiment == "positive":
                positions = [
                    "积极跟进，加大投入抢占技术制高点",
                    "谨慎评估，先小规模试点再决定",
                    "暂不跟进，专注现有技术路线",
                ]
            elif sig.sentiment == "negative":
                positions = [
                    "立即启动风险预案，寻找替代方案",
                    "保持观望，评估影响范围后再行动",
                    "逆势投入，认为风险中存在机会",
                ]
            else:
                positions = [
                    "认为该技术值得关注但时机未到",
                    "建议立即投入研发",
                    "不推荐跟进，优先级不足",
                ]

            topics.append(DebateTopicDraft(
                topic=topic,
                context=f"来源: {sig.source}\n{sig.title}\n{sig.description[:200]}" if sig.description else f"来源: {sig.source}\n{sig.title}",
                source_link=sig.link,
                category=sig.category,
                component_id=sig.component_id,
                tech_tags=sig.tech_tags,
                sentiment=sig.sentiment,
                suggested_positions=positions,
            ))

        return topics[:10]  # Limit to 10 topics

    def calculate_trend_adjustments(
        self,
        signals: list[IntelSignal],
        current_trends: dict[str, float],
    ) -> list[TrendAdjustment]:
        """Calculate trend weight adjustments based on RSS signal frequency and sentiment.

        If many positive RSS items mention a tech tag, boost its trend weight.
        If many negative items mention it, reduce the weight.
        """
        tag_signals: dict[str, list[float]] = {}

        for sig in signals:
            for tag in sig.tech_tags:
                if tag not in tag_signals:
                    tag_signals[tag] = []
                tag_signals[tag].append(sig.sentiment_score)

        adjustments: list[TrendAdjustment] = []
        for tag, scores in tag_signals.items():
            if len(scores) < 1:
                continue

            avg_sentiment = sum(scores) / len(scores)
            current_weight = current_trends.get(tag, 1.0)

            # Adjustment: ±0.1 per signal, capped at ±0.5
            adjustment = max(-0.5, min(0.5, avg_sentiment * 0.2))
            # More signals = stronger adjustment
            signal_strength = min(1.0, len(scores) / 5.0)
            adjustment *= signal_strength

            new_weight = max(0.3, min(3.0, current_weight + adjustment))

            if abs(new_weight - current_weight) < 0.01:
                continue

            if avg_sentiment > 0:
                reason = f"RSS情报偏向正面（{len(scores)}条信号，平均情感{avg_sentiment:+.2f}），趋势权重上调"
            elif avg_sentiment < 0:
                reason = f"RSS情报偏向负面（{len(scores)}条信号，平均情感{avg_sentiment:+.2f}），趋势权重下调"
            else:
                reason = f"RSS情报情感中性（{len(scores)}条信号），趋势权重微调"

            adjustments.append(TrendAdjustment(
                tag=tag,
                current_weight=round(current_weight, 2),
                adjusted_weight=round(new_weight, 2),
                reason=reason,
                signal_count=len(scores),
            ))

        return sorted(adjustments, key=lambda x: abs(x.adjusted_weight - x.current_weight), reverse=True)

    def summarize(self, signals: list[IntelSignal], current_trends: dict[str, float]) -> MarketIntelSummary:
        """Generate a market intelligence summary from all signals."""
        positive = sum(1 for s in signals if s.sentiment == "positive")
        negative = sum(1 for s in signals if s.sentiment == "negative")
        neutral = sum(1 for s in signals if s.sentiment == "neutral")

        # Tag frequency
        tag_counts: dict[str, int] = {}
        for sig in signals:
            for tag in sig.tech_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Category breakdown
        cat_breakdown: dict[str, int] = {}
        for sig in signals:
            cat_breakdown[sig.category] = cat_breakdown.get(sig.category, 0) + 1

        # Key events (top by severity)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_sigs = sorted(signals, key=lambda s: severity_order.get(s.severity, 4))
        key_events = [s.title for s in sorted_sigs[:5]]

        # Trend adjustments
        adjustments = self.calculate_trend_adjustments(signals, current_trends)

        return MarketIntelSummary(
            total_signals=len(signals),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            top_tags=top_tags,
            category_breakdown=cat_breakdown,
            key_events=key_events,
            trend_adjustments=adjustments,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
