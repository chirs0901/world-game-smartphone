"""World service — world state queries and knowledge graph."""

from src.engines.knowledge_graph import KnowledgeGraph
from src.schemas.world import Entity, EntityType, KnowledgeGraphResponse


class WorldService:
    """Provides world state and knowledge graph queries."""

    def __init__(self):
        self.kg = KnowledgeGraph()

    def get_entities(
        self, entity_type: str | None = None
    ) -> list[Entity]:
        """List entities, optionally filtered by type."""
        etype = EntityType(entity_type) if entity_type else None
        return self.kg.find_entities(entity_type=etype)

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get a single entity by ID."""
        return self.kg.get_entity(entity_id)

    def get_knowledge_graph(
        self, root_ids: list[str] | None = None, depth: int = 2
    ) -> KnowledgeGraphResponse:
        """Get knowledge graph data for visualization."""
        if root_ids:
            subgraph = self.kg.get_subgraph(root_ids, depth=depth)
        else:
            # Return all entities and edges
            all_ids = list(self.kg.entities.keys())
            subgraph = self.kg.get_subgraph(all_ids[:20], depth=depth)

        return KnowledgeGraphResponse(
            nodes=subgraph["nodes"],
            edges=subgraph["edges"],
        )
