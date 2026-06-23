"""RSS Intelligence API routes — RSS-driven game content."""

from fastapi import APIRouter, Depends, Query

from src.dependencies import get_rss_service, get_rss_intel_engine
from src.engines.rss_intel import RSSIntelEngine
from src.engines.tech_roadmap import TechRoadmapEngine
from src.services.rss_service import RSSService

router = APIRouter()

_tech_engine = TechRoadmapEngine()


@router.get("/rss/intel/events")
async def get_rss_events(
    refresh: bool = Query(False, description="Force refresh RSS before analyzing"),
    rss_svc: RSSService = Depends(get_rss_service),
    intel_engine: RSSIntelEngine = Depends(get_rss_intel_engine),
):
    """Generate game events from RSS intelligence signals.

    These events are derived from real-time industry news and can be
    used as the basis for game events, debate topics, and tech trends.
    """
    if refresh or not rss_svc.get_cached():
        await rss_svc.fetch_all()

    items = rss_svc.get_cached()
    signals = intel_engine.analyze_items(items)
    events = intel_engine.generate_game_events(signals)

    return {
        "count": len(events),
        "events": [
            {
                "title": e.title,
                "description": e.description,
                "category": e.category,
                "severity": e.severity,
                "source_rss": e.source_rss,
                "source_link": e.source_link,
                "component_id": e.component_id,
                "tech_tags": e.tech_tags,
                "sentiment": e.sentiment,
                "impacts": e.impacts,
                "response_options": e.response_options,
                "rss_driven": e.rss_driven,
            }
            for e in events
        ],
    }


@router.get("/rss/intel/debates")
async def get_rss_debates(
    refresh: bool = Query(False),
    rss_svc: RSSService = Depends(get_rss_service),
    intel_engine: RSSIntelEngine = Depends(get_rss_intel_engine),
):
    """Generate debate topics for AI board from RSS intelligence."""
    if refresh or not rss_svc.get_cached():
        await rss_svc.fetch_all()

    items = rss_svc.get_cached()
    signals = intel_engine.analyze_items(items)
    topics = intel_engine.generate_debate_topics(signals)

    return {
        "count": len(topics),
        "topics": [
            {
                "topic": t.topic,
                "context": t.context,
                "source_link": t.source_link,
                "category": t.category,
                "component_id": t.component_id,
                "tech_tags": t.tech_tags,
                "sentiment": t.sentiment,
                "suggested_positions": t.suggested_positions,
            }
            for t in topics
        ],
    }


@router.get("/rss/intel/trends")
async def get_rss_trends(
    period: str = Query("short_term", description="Market period: short_term/mid_term/long_term"),
    refresh: bool = Query(False),
    rss_svc: RSSService = Depends(get_rss_service),
    intel_engine: RSSIntelEngine = Depends(get_rss_intel_engine),
):
    """Get tech trend weight adjustments derived from RSS intelligence.

    The returned adjusted weights can be used to override the static
    MARKET_TRENDS in the tech roadmap engine for real-time adaptation.
    """
    if refresh or not rss_svc.get_cached():
        await rss_svc.fetch_all()

    items = rss_svc.get_cached()
    signals = intel_engine.analyze_items(items)
    current_trends = _tech_engine.get_market_trends(period)
    adjustments = intel_engine.calculate_trend_adjustments(signals, current_trends)

    # Build merged trends (current + adjustments)
    merged_trends = dict(current_trends)
    for adj in adjustments:
        merged_trends[adj.tag] = adj.adjusted_weight

    return {
        "period": period,
        "original_trends": current_trends,
        "merged_trends": merged_trends,
        "adjustments": [
            {
                "tag": a.tag,
                "current_weight": a.current_weight,
                "adjusted_weight": a.adjusted_weight,
                "reason": a.reason,
                "signal_count": a.signal_count,
            }
            for a in adjustments
        ],
    }


@router.get("/rss/intel/summary")
async def get_rss_summary(
    period: str = Query("short_term"),
    refresh: bool = Query(False),
    rss_svc: RSSService = Depends(get_rss_service),
    intel_engine: RSSIntelEngine = Depends(get_rss_intel_engine),
):
    """Get a comprehensive market intelligence summary from RSS feeds."""
    if refresh or not rss_svc.get_cached():
        await rss_svc.fetch_all()

    items = rss_svc.get_cached()
    signals = intel_engine.analyze_items(items)
    current_trends = _tech_engine.get_market_trends(period)
    summary = intel_engine.summarize(signals, current_trends)

    return {
        "total_signals": summary.total_signals,
        "positive_count": summary.positive_count,
        "negative_count": summary.negative_count,
        "neutral_count": summary.neutral_count,
        "top_tags": [{"tag": t, "count": c} for t, c in summary.top_tags],
        "category_breakdown": summary.category_breakdown,
        "key_events": summary.key_events,
        "trend_adjustments": [
            {
                "tag": a.tag,
                "current_weight": a.current_weight,
                "adjusted_weight": a.adjusted_weight,
                "reason": a.reason,
                "signal_count": a.signal_count,
            }
            for a in summary.trend_adjustments
        ],
        "generated_at": summary.generated_at,
    }
