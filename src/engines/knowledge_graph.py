"""Knowledge graph engine — in-memory graph with JSON file storage."""

import json
from collections import deque
from pathlib import Path
from typing import Optional

from src.schemas.world import Entity, EntityRelation, EntityType
from src.utils.config import get_data_dir
from src.utils.logging import logger


class KnowledgeGraph:
    """In-memory knowledge graph loaded from JSON files.

    Provides graph operations (neighbors, subgraph, paths) for use by
    the simulation engine and frontend visualization.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.entities: dict[str, Entity] = {}
        self._adjacency: dict[str, list[EntityRelation]] = {}
        kg_dir = Path(data_dir) if data_dir else get_data_dir() / "knowledge_graph"
        self._load(kg_dir)

    def _load(self, kg_dir: Path) -> None:
        """Load all JSON entity files from the knowledge_graph directory."""
        if not kg_dir.exists():
            logger.warning("Knowledge graph directory not found", path=str(kg_dir))
            return

        for json_file in sorted(kg_dir.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for item in data:
                    entity = Entity(
                        id=item["id"],
                        type=EntityType(item["type"]),
                        name=item["name"],
                        attributes=item.get("attributes", {}),
                        relations=[
                            EntityRelation(**r) for r in item.get("relations", [])
                        ],
                    )
                    self.entities[entity.id] = entity
                    self._adjacency[entity.id] = entity.relations

                logger.info("Loaded knowledge graph file", file=json_file.name, count=len(data))
            except Exception as e:
                logger.error("Failed to load KG file", file=json_file.name, error=str(e))

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)

    def find_entities(
        self,
        entity_type: Optional[EntityType] = None,
        **filters,
    ) -> list[Entity]:
        """Find entities by type and/or attribute filters."""
        results = []
        for entity in self.entities.values():
            if entity_type and entity.type != entity_type:
                continue
            if filters:
                match = all(
                    entity.attributes.get(k) == v for k, v in filters.items()
                )
                if not match:
                    continue
            results.append(entity)
        return results

    def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        depth: int = 1,
    ) -> list[Entity]:
        """Get neighboring entities up to a given depth.

        Args:
            entity_id: Starting entity
            relation_type: Filter by relation type (None = all)
            depth: How many hops to traverse (1 = direct neighbors only)
        """
        visited: set[str] = {entity_id}
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])
        neighbors: list[Entity] = []

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            for rel in self._adjacency.get(current_id, []):
                if relation_type and rel.relation_type != relation_type:
                    continue
                if rel.target_id not in visited:
                    visited.add(rel.target_id)
                    target = self.entities.get(rel.target_id)
                    if target:
                        neighbors.append(target)
                        queue.append((rel.target_id, current_depth + 1))

        return neighbors

    def get_subgraph(
        self,
        root_ids: list[str],
        depth: int = 2,
    ) -> dict:
        """Extract a subgraph rooted at given nodes.

        Returns dict with 'nodes' and 'edges' for visualization.
        """
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        nodes: list[dict] = []
        edges: list[dict] = []

        for rid in root_ids:
            if rid in self.entities:
                visited.add(rid)
                queue.append((rid, 0))

        while queue:
            current_id, current_depth = queue.popleft()
            entity = self.entities[current_id]
            nodes.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type.value,
                "attributes": entity.attributes,
            })

            if current_depth >= depth:
                continue

            for rel in self._adjacency.get(current_id, []):
                edges.append({
                    "source": current_id,
                    "target": rel.target_id,
                    "type": rel.relation_type,
                    "weight": rel.weight,
                })
                if rel.target_id not in visited and rel.target_id in self.entities:
                    visited.add(rel.target_id)
                    queue.append((rel.target_id, current_depth + 1))

        return {"nodes": nodes, "edges": edges}

    def find_paths(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 3,
    ) -> list[list[str]]:
        """Find relationship paths between two entities (BFS)."""
        if from_id not in self.entities or to_id not in self.entities:
            return []

        paths: list[list[str]] = []
        queue: deque[list[str]] = deque([[from_id]])

        while queue:
            path = queue.popleft()
            if len(path) - 1 >= max_depth:
                continue

            current = path[-1]
            for rel in self._adjacency.get(current, []):
                if rel.target_id == to_id:
                    paths.append(path + [to_id])
                elif rel.target_id not in path:
                    queue.append(path + [rel.target_id])

        return paths

    def get_related_context(
        self,
        decision_category: str,
        max_entities: int = 10,
    ) -> str:
        """Build a text context string for the simulation engine.

        Extracts relevant entities based on decision category and
        formats them as a readable text summary.
        """
        # Map decision categories to relevant entity types
        type_map = {
            "rd": [EntityType.TECHNOLOGY, EntityType.SUPPLIER],
            "product": [EntityType.TECHNOLOGY, EntityType.PRODUCT],
            "supply": [EntityType.SUPPLIER],
            "marketing": [EntityType.BRAND],
            "finance": [EntityType.BRAND, EntityType.SUPPLIER],
            "hr": [EntityType.PERSON],
        }

        relevant_types = type_map.get(decision_category, [EntityType.BRAND])
        entities = []
        for etype in relevant_types:
            entities.extend(self.find_entities(entity_type=etype))

        # Limit to max_entities
        entities = entities[:max_entities]

        if not entities:
            return "（无相关知识图谱数据）"

        lines = []
        for e in entities:
            attrs = ", ".join(f"{k}={v}" for k, v in list(e.attributes.items())[:5])
            rels = ", ".join(
                f"--{r.relation_type}--> {self.entities.get(r.target_id, Entity(id=r.target_id, type=EntityType.BRAND, name=r.target_id)).name}"
                for r in e.relations[:3]
            )
            line = f"- {e.name} ({e.type.value})"
            if attrs:
                line += f" [{attrs}]"
            if rels:
                line += f" | 关系: {rels}"
            lines.append(line)

        return "\n".join(lines)
