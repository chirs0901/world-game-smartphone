"""Game management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_game_service
from src.schemas.game import (
    CompanyOption,
    GameConfig,
    GameSessionCreate,
    GameSessionResponse,
    MarketActivitySnapshot,
    TurnSummary,
)
from src.schemas.simulation import PlayerDecision
from src.schemas.world import WorldState
from src.services.game_service import GameService

router = APIRouter()


@router.get("/companies", response_model=list[CompanyOption])
async def list_companies(
    svc: GameService = Depends(get_game_service),
):
    """Get all available companies for the player to choose from."""
    return svc.get_companies()


@router.post("", response_model=GameSessionResponse)
async def create_game(
    request: GameSessionCreate | None = None,
    db: AsyncSession = Depends(get_db),
    svc: GameService = Depends(get_game_service),
):
    """Create a new game session."""
    if request is None:
        request = GameSessionCreate()
    result = await svc.create_game(db, request)
    await db.commit()
    return result


@router.get("/{game_id}", response_model=GameSessionResponse)
async def get_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    svc: GameService = Depends(get_game_service),
):
    """Get game session status."""
    result = await svc.get_game(db, game_id)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found")
    return result


@router.get("/{game_id}/world-state", response_model=WorldState)
async def get_game_world_state(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    svc: GameService = Depends(get_game_service),
):
    """Get the current world state for a game."""
    state = await svc.get_world_state(db, game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game or world state not found")
    return state


@router.get("/{game_id}/market-activity", response_model=MarketActivitySnapshot)
async def get_market_activity(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    svc: GameService = Depends(get_game_service),
):
    """Get real-time market activity snapshot for the store animation."""
    try:
        activity = await svc.get_market_activity(db, game_id)
        return activity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{game_id}/next-turn", response_model=TurnSummary)
async def next_turn(
    game_id: str,
    decisions: list[PlayerDecision] | None = None,
    db: AsyncSession = Depends(get_db),
    svc: GameService = Depends(get_game_service),
):
    """Advance the game to the next turn."""
    try:
        summary = await svc.advance_turn(
            db, game_id, decisions or [], []
        )
        await db.commit()
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
