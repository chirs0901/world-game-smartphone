"""RSS feed API routes."""

from fastapi import APIRouter, Depends, Query

from src.dependencies import get_rss_service
from src.services.rss_service import RSSService

router = APIRouter()


@router.get("/rss/feeds")
async def list_feeds(rss_svc: RSSService = Depends(get_rss_service)):
    """List all RSS feed sources."""
    feeds = rss_svc.get_feeds()
    return {
        "feeds": [
            {
                "name": f.name,
                "category": f.category,
                "xml_url": f.xml_url,
                "html_url": f.html_url,
            }
            for f in feeds
        ],
        "categories": rss_svc.get_categories(),
    }


@router.get("/rss/items")
async def list_items(
    refresh: bool = Query(False, description="Force refresh from sources"),
    category: str = Query("", description="Filter by category"),
    rss_svc: RSSService = Depends(get_rss_service),
):
    """Get aggregated RSS items. Set refresh=true to fetch from sources."""
    if refresh:
        await rss_svc.fetch_all()

    items = rss_svc.get_cached()
    if category:
        items = [i for i in items if i.source_category == category]

    return {
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "description": i.description,
                "link": i.link,
                "source_name": i.source_name,
                "source_category": i.source_category,
                "published": i.published,
            }
            for i in items[:30]
        ]
    }


@router.get("/rss/refresh")
async def refresh_feeds(rss_svc: RSSService = Depends(get_rss_service)):
    """Force refresh all RSS feeds."""
    items = await rss_svc.fetch_all()
    return {
        "count": len(items),
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "source_name": i.source_name,
                "source_category": i.source_category,
            }
            for i in items[:30]
        ],
    }
