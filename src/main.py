"""World Game API entry point."""

import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.db.session import init_db

load_dotenv()

# Background task handle
_background_tasks: list[asyncio.Task] = []


async def _rss_refresh_loop():
    """Background task: Refresh RSS feeds every 30 minutes and feed intel pipeline.

    After fetching fresh RSS items, the pipeline automatically:
    1. Analyzes items into IntelSignals (RSSIntelEngine)
    2. Generates game event drafts → feeds into EventGenerator
    3. Calculates trend adjustments → feeds into TechRoadmapEngine
    4. Generates debate topics → feeds into AI Board/Simulation

    These become available as cached data for all downstream systems.
    """
    # Wait for full app startup before first refresh
    await asyncio.sleep(10)

    from src.dependencies import _rss_service, _rss_intel_engine, _tech_roadmap_engine

    RSS_REFRESH_INTERVAL = 30 * 60  # 30 minutes

    while True:
        try:
            print("[RSS-BG] Starting scheduled RSS refresh...")
            items = await _rss_service.fetch_all()
            print(f"[RSS-BG] Fetched {len(items)} items from {len(_rss_service.get_feeds())} feeds")

            if items:
                # Run through intel pipeline to warm cache
                signals = _rss_intel_engine.analyze_items(items)
                print(f"[RSS-BG] Generated {len(signals)} intel signals")

                # Also update tech roadmap trends cache
                from src.engines.tech_roadmap import TechRoadmapEngine
                if _tech_roadmap_engine:
                    trends = _tech_roadmap_engine.get_market_trends("short_term")
                    adjustments = _rss_intel_engine.calculate_trend_adjustments(signals, trends)
                    print(f"[RSS-BG] Calculated {len(adjustments)} trend adjustments")

        except Exception as e:
            print(f"[RSS-BG] Refresh failed: {e}")

        await asyncio.sleep(RSS_REFRESH_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup: initialize database
    await init_db()

    # Start RSS background refresh loop
    task = asyncio.create_task(_rss_refresh_loop())
    _background_tasks.append(task)

    yield

    # Shutdown: cancel background tasks
    for t in _background_tasks:
        t.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)


def create_app() -> FastAPI:
    app = FastAPI(
        title="World Game API",
        description="AI-Driven Industry World Model Simulation Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
