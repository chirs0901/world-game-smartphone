"""Intel center API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_intel_service
from src.schemas.intel import GameEvent, NewsItem
from src.services.intel_service import IntelService

router = APIRouter()


@router.get("/game/{game_id}/intel/events", response_model=list[GameEvent])
async def list_events(
    game_id: str,
    turn: int | None = None,
    db: AsyncSession = Depends(get_db),
    svc: IntelService = Depends(get_intel_service),
):
    """List intel events for a game, optionally filtered by turn."""
    return await svc.list_events(db, game_id, turn=turn)


@router.get("/game/{game_id}/intel/events/{event_id}", response_model=GameEvent)
async def get_event_detail(
    game_id: str,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    svc: IntelService = Depends(get_intel_service),
):
    """Get a single event by ID."""
    result = await svc.get_event_detail(db, event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.get("/game/{game_id}/intel/news", response_model=list[NewsItem])
async def list_news(
    game_id: str,
    turn: int | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    svc: IntelService = Depends(get_intel_service),
):
    """List news items with optional filtering."""
    return await svc.list_news(
        db, game_id, turn=turn, category=category, page=page, page_size=page_size
    )
