"""OKR service — objectives and key results management."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.okr import KeyResultModel, ObjectiveModel
from src.schemas.okr import KeyResult, KRStatus, Objective, ObjectiveCreate, OKRSummary, OKRUpdate
from src.schemas.world import BrandMetrics


class OKRService:
    """CRUD and progress tracking for OKRs."""

    async def create_objective(
        self, db: AsyncSession, game_id: str, turn: int, request: ObjectiveCreate
    ) -> Objective:
        obj_id = str(uuid.uuid4())
        model = ObjectiveModel(
            id=obj_id,
            game_id=game_id,
            turn_created=turn,
            title=request.title,
            description=request.description,
            priority=request.priority,
        )
        db.add(model)

        krs = []
        for kr in request.key_results:
            kr_id = str(uuid.uuid4())
            kr_model = KeyResultModel(
                id=kr_id,
                objective_id=obj_id,
                title=kr.title,
                metric=kr.metric,
                target_value=kr.target_value,
                current_value=kr.current_value,
                unit=kr.unit,
            )
            db.add(kr_model)
            krs.append(KeyResult(id=kr_id, title=kr.title, metric=kr.metric,
                                 target_value=kr.target_value, unit=kr.unit))

        await db.flush()
        return Objective(
            id=obj_id, game_id=game_id, turn_created=turn,
            title=request.title, description=request.description,
            key_results=krs, priority=request.priority,
        )

    async def list_objectives(
        self, db: AsyncSession, game_id: str, active_only: bool = True
    ) -> list[Objective]:
        query = select(ObjectiveModel).where(ObjectiveModel.game_id == game_id)
        if active_only:
            query = query.where(ObjectiveModel.is_active == True)
        query = query.order_by(ObjectiveModel.priority, ObjectiveModel.created_at)

        result = await db.execute(query)
        objectives = []
        for model in result.scalars():
            krs = await self._get_key_results(db, model.id)
            objectives.append(Objective(
                id=model.id, game_id=model.game_id, turn_created=model.turn_created,
                title=model.title, description=model.description,
                key_results=krs, priority=model.priority, is_active=model.is_active,
            ))
        return objectives

    async def update_kr_progress(
        self, db: AsyncSession, update: OKRUpdate
    ) -> KeyResult | None:
        result = await db.execute(
            select(KeyResultModel).where(KeyResultModel.id == update.key_result_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        model.current_value = update.new_value
        if model.target_value > 0:
            model.progress = min(1.0, update.new_value / model.target_value)
        if model.progress >= 1.0:
            model.status = "achieved"
        elif model.progress >= 0.7:
            model.status = "in_progress"
        else:
            model.status = "not_started"

        await db.flush()
        return KeyResult(
            id=model.id, title=model.title, metric=model.metric,
            target_value=model.target_value, current_value=model.current_value,
            unit=model.unit, status=KRStatus(model.status), progress=model.progress,
        )

    async def auto_update_progress(
        self, db: AsyncSession, game_id: str, metrics: BrandMetrics
    ) -> None:
        """Auto-update KR progress based on current brand metrics."""
        objectives = await self.list_objectives(db, game_id, active_only=True)
        for obj in objectives:
            for kr in obj.key_results:
                current = getattr(metrics, kr.metric, None)
                if current is not None:
                    await self.update_kr_progress(
                        db, OKRUpdate(key_result_id=kr.id, new_value=current)
                    )

    async def get_summary(self, db: AsyncSession, game_id: str) -> OKRSummary:
        objectives = await self.list_objectives(db, game_id, active_only=True)
        total = len(objectives)
        completed = sum(1 for o in objectives if all(kr.status == KRStatus.ACHIEVED for kr in o.key_results) and o.key_results)
        on_track = sum(1 for o in objectives if any(kr.progress >= 0.5 for kr in o.key_results))
        return OKRSummary(total=total, completed=completed, on_track=on_track, at_risk=total - on_track)

    async def _get_key_results(self, db: AsyncSession, objective_id: str) -> list[KeyResult]:
        result = await db.execute(
            select(KeyResultModel).where(KeyResultModel.objective_id == objective_id)
        )
        return [
            KeyResult(
                id=m.id, title=m.title, metric=m.metric,
                target_value=m.target_value, current_value=m.current_value,
                unit=m.unit, status=KRStatus(m.status), progress=m.progress,
            )
            for m in result.scalars()
        ]
