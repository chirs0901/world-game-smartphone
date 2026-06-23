"""World state API routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_world_service
from src.schemas.world import Entity, KnowledgeGraphResponse
from src.services.world_service import WorldService

router = APIRouter()


@router.get("/world/entities", response_model=list[Entity])
async def list_entities(
    entity_type: str | None = None,
    svc: WorldService = Depends(get_world_service),
):
    """List knowledge graph entities, optionally filtered by type."""
    return svc.get_entities(entity_type=entity_type)


@router.get("/world/entities/{entity_id}", response_model=Entity)
async def get_entity(
    entity_id: str,
    svc: WorldService = Depends(get_world_service),
):
    """Get a single entity by ID."""
    result = svc.get_entity(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result


@router.get("/world/knowledge-graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    root_ids: str | None = None,
    depth: int = 2,
    svc: WorldService = Depends(get_world_service),
):
    """Get knowledge graph data for visualization."""
    ids = root_ids.split(",") if root_ids else None
    return svc.get_knowledge_graph(root_ids=ids, depth=depth)
