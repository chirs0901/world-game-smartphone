"""Intel service — news and event management."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.intel import EventRecordModel, NewsRecordModel
from src.schemas.intel import GameEvent, NewsItem


class IntelService:
    """Manages news items and game events."""

    async def save_events(
        self, db: AsyncSession, game_id: str, events: list[GameEvent]
    ) -> None:
        """Persist game events to database."""
        for event in events:
            model = EventRecordModel(
                id=event.id or str(uuid.uuid4()),
                game_id=game_id,
                turn=event.turn,
                event_json=event.model_dump_json(),
                severity=event.severity.value,
            )
            db.add(model)
        await db.flush()

    async def save_news(
        self, db: AsyncSession, game_id: str, news_items: list[dict]
    ) -> None:
        """Persist news items to database."""
        for item in news_items:
            model = NewsRecordModel(
                id=item.get("id", str(uuid.uuid4())),
                game_id=game_id,
                turn=item["turn"],
                category=item["category"],
                headline=item["headline"],
                content=item["content"],
                source=item.get("source", ""),
                sentiment=item.get("sentiment", "neutral"),
                is_critical=item.get("is_critical", False),
                tags_json=str(item.get("tags", [])),
            )
            db.add(model)
        await db.flush()

    async def list_events(
        self, db: AsyncSession, game_id: str, turn: int | None = None
    ) -> list[GameEvent]:
        """List game events, optionally filtered by turn."""
        query = select(EventRecordModel).where(EventRecordModel.game_id == game_id)
        if turn is not None:
            query = query.where(EventRecordModel.turn == turn)
        query = query.order_by(EventRecordModel.created_at.desc())

        result = await db.execute(query)
        events = []
        for model in result.scalars():
            event = GameEvent.model_validate_json(model.event_json)
            event.id = model.id
            events.append(event)
        return events

    async def list_news(
        self, db: AsyncSession, game_id: str, turn: int | None = None,
        category: str | None = None, page: int = 1, page_size: int = 20,
    ) -> list[NewsItem]:
        """List news items with optional filtering."""
        query = select(NewsRecordModel).where(NewsRecordModel.game_id == game_id)
        if turn is not None:
            query = query.where(NewsRecordModel.turn == turn)
        if category:
            query = query.where(NewsRecordModel.category == category)
        query = query.order_by(NewsRecordModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        return [
            NewsItem(
                id=m.id, turn=m.turn, headline=m.headline, content=m.content,
                source=m.source, is_critical=m.is_critical,
            )
            for m in result.scalars()
        ]

    async def get_active_events(
        self, db: AsyncSession, game_id: str, current_turn: int
    ) -> list[GameEvent]:
        """Get events that are still active at the current turn.

        An event is active if current_turn is within [event.turn, event.turn + duration_turns - 1].
        """
        # Query events from current and recent turns
        query = (
            select(EventRecordModel)
            .where(EventRecordModel.game_id == game_id)
            .where(EventRecordModel.turn <= current_turn)
            .order_by(EventRecordModel.created_at.desc())
        )
        result = await db.execute(query)

        active: list[GameEvent] = []
        for model in result.scalars():
            event = GameEvent.model_validate_json(model.event_json)
            event.id = model.id
            # Check if the event is still within its duration
            expires_at = event.turn + event.duration_turns - 1
            if current_turn <= expires_at:
                active.append(event)
        return active

    async def get_event_detail(
        self, db: AsyncSession, event_id: str
    ) -> GameEvent | None:
        """Get a single event by ID."""
        result = await db.execute(
            select(EventRecordModel).where(EventRecordModel.id == event_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        event = GameEvent.model_validate_json(model.event_json)
        event.id = model.id
        return event
