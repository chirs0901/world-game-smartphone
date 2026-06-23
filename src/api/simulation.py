"""Simulation sandbox API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_game_service, get_intel_service, get_simulation_service
from src.schemas.intel import GameEvent
from src.schemas.simulation import (
    PlayerDecision,
    SimulateRequest,
    SimulateResponse,
    SimulationResult,
)
from src.services.game_service import GameService
from src.services.simulation_service import SimulationService

router = APIRouter()


@router.post("/game/{game_id}/simulate", response_model=SimulateResponse)
async def simulate_decisions(
    game_id: str,
    request: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    game_svc: GameService = Depends(get_game_service),
    sim_svc: SimulationService = Depends(get_simulation_service),
    intel_svc = Depends(get_intel_service),
):
    """Simulate decisions against the current world state."""
    state = await game_svc.get_world_state(db, game_id)
    if not state:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Game not found")

    # Fetch active events from intel service
    events = await intel_svc.get_active_events(db, game_id, state.turn)

    results = await sim_svc.simulate_decisions(request.decisions, state, events)
    total_cost = sum(d.budget or 0 for d in request.decisions)
    return SimulateResponse(results=results, total_cost=total_cost)
