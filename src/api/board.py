"""AI board API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_board_service
from src.schemas.board import AgentProfile, DebateRequest, DebateResponse
from src.services.board_service import BoardService

router = APIRouter()


@router.get("/game/{game_id}/board/agents", response_model=list[AgentProfile])
async def list_agents(
    game_id: str,
    svc: BoardService = Depends(get_board_service),
):
    """List all AI board agents."""
    return svc.get_agents()


@router.post("/game/{game_id}/board/debate", response_model=DebateResponse)
async def run_debate(
    game_id: str,
    request: DebateRequest,
    turn: int = 1,
    db: AsyncSession = Depends(get_db),
    svc: BoardService = Depends(get_board_service),
):
    """Run a full AI board debate."""
    result = await svc.run_debate(db, game_id, turn, request)
    await db.commit()
    return result


@router.get("/game/{game_id}/board/debates", response_model=list[DebateResponse])
async def get_debate_history(
    game_id: str,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    svc: BoardService = Depends(get_board_service),
):
    """Get debate history for a game."""
    return await svc.get_debate_history(db, game_id, page=page, page_size=page_size)
