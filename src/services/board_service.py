"""Board service — orchestrates AI board debates."""

from typing import Optional
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.agent import AgentSystem
from src.engines.claim_debate import ClaimDebateEngine
from src.llm.client import LLMClient
from src.models.board import AgentStateModel, DebateRecordModel
from src.schemas.board import (
    AgentMemory,
    AgentProfile,
    BoardDecision,
    DebateRequest,
    DebateResponse,
    DebateRound,
)


class BoardService:
    """Orchestrates AI board debates and persists results."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.agent_system = AgentSystem(llm=llm_client)
        self.debate_engine = ClaimDebateEngine(self.agent_system, llm=llm_client)

    async def run_debate(
        self, db: AsyncSession, game_id: str, turn: int, request: DebateRequest
    ) -> DebateResponse:
        """Run a full debate and persist the results."""
        debate_id = str(uuid.uuid4())

        rounds, decision = await self.debate_engine.run_debate(
            topic=request.topic,
            context=request.context,
            options=request.options,
        )

        # Persist debate record
        model = DebateRecordModel(
            id=debate_id,
            game_id=game_id,
            turn=turn,
            topic=request.topic,
            rounds_json=json.dumps([r.model_dump() for r in rounds]) if rounds else "[]",
            decision_json=decision.model_dump_json(),
        )
        db.add(model)
        await db.flush()

        # Serialize rounds properly
        rounds_data = []
        for r in rounds:
            rounds_data.append(r.model_dump())

        return DebateResponse(
            debate_id=debate_id,
            rounds=rounds,
            decision=decision,
            status="concluded",
        )

    def get_agents(self) -> list[AgentProfile]:
        """Return all agent profiles."""
        return self.agent_system.get_profiles()

    async def get_debate_history(
        self, db: AsyncSession, game_id: str, page: int = 1, page_size: int = 10
    ) -> list[DebateResponse]:
        """Get debate history."""
        query = (
            select(DebateRecordModel)
            .where(DebateRecordModel.game_id == game_id)
            .order_by(DebateRecordModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        debates = []
        for model in result.scalars():
            decision = BoardDecision.model_validate_json(model.decision_json)
            debates.append(DebateResponse(
                debate_id=model.id,
                decision=decision,
                status="concluded",
            ))
        return debates
