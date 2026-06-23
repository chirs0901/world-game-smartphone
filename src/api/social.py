"""Social media monitoring API routes — Xiaohongshu brand tracking."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import unquote

from src.dependencies import get_social_service
from src.services.social_service import SocialService

router = APIRouter()


@router.get("/social/xhs-posts")
async def get_xhs_posts(
    brand: str = Query("apply", description="Brand ID (e.g. apply, samsun, huawey)"),
    force_refresh: bool = Query(False, description="Force refresh, bypass cache"),
    svc: SocialService = Depends(get_social_service),
):
    """Get top Xiaohongshu posts about the specified brand.

    Returns up to 20 posts sorted by likes, cached for 2 hours.
    Set force_refresh=true to trigger a new search.
    """
    return svc.search_xhs_posts(brand, limit=20, force_refresh=force_refresh)


@router.get("/social/image-proxy")
async def proxy_image(
    url: str = Query(..., description="Image URL to proxy"),
):
    """Proxy external images to avoid hotlink blocking.

    Xiaohongshu images require Referer header, which browsers
    won't send from a different origin. This proxy fetches the
    image server-side with proper headers.
    """
    decoded_url = unquote(url)
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                decoded_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Referer": "https://www.xiaohongshu.com/",
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                },
            )
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "image/jpeg")
                return StreamingResponse(
                    content=resp.aiter_bytes(),
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
    except Exception:
        pass
    # Return a transparent 1x1 pixel on failure
    return StreamingResponse(
        content=iter([b""]),
        media_type="image/gif",
        status_code=204,
    )
