"""OKR workspace API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_okr_service
from src.schemas.okr import KeyResult, Objective, ObjectiveCreate, OKRSummary, OKRUpdate
from src.services.okr_service import OKRService

router = APIRouter()


@router.get("/game/{game_id}/okr", response_model=list[Objective])
async def list_objectives(
    game_id: str,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    svc: OKRService = Depends(get_okr_service),
):
    """List all objectives for a game."""
    return await svc.list_objectives(db, game_id, active_only=active_only)


@router.post("/game/{game_id}/okr", response_model=Objective)
async def create_objective(
    game_id: str,
    request: ObjectiveCreate,
    turn: int = 1,
    db: AsyncSession = Depends(get_db),
    svc: OKRService = Depends(get_okr_service),
):
    """Create a new objective."""
    result = await svc.create_objective(db, game_id, turn, request)
    await db.commit()
    return result


@router.put("/game/{game_id}/okr/progress", response_model=KeyResult)
async def update_kr_progress(
    game_id: str,
    update: OKRUpdate,
    db: AsyncSession = Depends(get_db),
    svc: OKRService = Depends(get_okr_service),
):
    """Update key result progress."""
    result = await svc.update_kr_progress(db, update)
    if not result:
        raise HTTPException(status_code=404, detail="Key result not found")
    await db.commit()
    return result


@router.get("/game/{game_id}/okr/summary", response_model=OKRSummary)
async def get_okr_summary(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    svc: OKRService = Depends(get_okr_service),
):
    """Get OKR summary for a game."""
    return await svc.get_summary(db, game_id)
