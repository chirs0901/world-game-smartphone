"""Game service — manages game lifecycle and turn progression."""

import random
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.event_generator import EventGenerator
from src.engines.knowledge_graph import KnowledgeGraph
from src.engines.rss_intel import RSSIntelEngine
from src.engines.simulation import SimulationEngine
from src.engines.state_machine import WorldStateMachine
from src.models.game import GameSessionModel, TurnModel
from src.models.world import WorldSnapshotModel
from src.schemas.game import (
    CompanyOption,
    GameConfig,
    GameSessionCreate,
    GameSessionResponse,
    MarketActivity,
    MarketActivitySnapshot,
    TurnSummary,
)
from src.schemas.world import WorldState
from src.services.intel_service import IntelService
from src.services.rss_service import RSSService
from src.utils.config import load_yaml
from src.utils.logging import logger


class GameService:
    """Orchestrates game creation, turn advancement, and state persistence."""

    def __init__(
        self,
        rss_service: RSSService | None = None,
        rss_intel_engine: RSSIntelEngine | None = None,
    ):
        self.kg = KnowledgeGraph()
        self.state_machine = WorldStateMachine(self.kg)
        # RSS-driven event generation (creates own instances if not injected)
        self.rss_service = rss_service or RSSService()
        self.rss_intel_engine = rss_intel_engine or RSSIntelEngine()
        self.event_generator = EventGenerator(
            kg=self.kg,
            rss_service=self.rss_service,
            rss_intel_engine=self.rss_intel_engine,
        )
        self.simulation_engine = SimulationEngine(
            kg=self.kg,
            rss_service=self.rss_service,
            rss_intel_engine=self.rss_intel_engine,
        )
        self.intel_service = IntelService()

    def get_companies(self) -> list[CompanyOption]:
        """Return all available companies for selection."""
        companies = self.state_machine.get_companies()
        return [CompanyOption(**c) for c in companies]

    def get_company_name(self, company_id: str) -> str:
        """Get company display name."""
        company = self.state_machine.get_company(company_id)
        return company["name"] if company else company_id

    async def create_game(self, db: AsyncSession, request: GameSessionCreate) -> GameSessionResponse:
        """Create a new game session with initial world state."""
        config = request.config
        game_id = str(uuid.uuid4())

        # Create initial world state with company-specific metrics
        initial_state = self.state_machine.create_initial_state(
            difficulty=config.difficulty,
            company_id=config.company_id,
        )

        # Persist game session
        session_model = GameSessionModel(
            id=game_id,
            status="active",
            config_json=config.model_dump_json(),
            current_turn=initial_state.turn,
            current_year=initial_state.year,
            current_quarter=initial_state.quarter,
        )
        db.add(session_model)

        # Save initial world snapshot
        snapshot = WorldSnapshotModel(
            id=str(uuid.uuid4()),
            game_id=game_id,
            turn=initial_state.turn,
            state_json=initial_state.model_dump_json(),
            delta_json="{}",
        )
        db.add(snapshot)

        company_name = self.get_company_name(config.company_id)

        # Save initial turn record
        turn_model = TurnModel(
            id=str(uuid.uuid4()),
            game_id=game_id,
            turn_number=initial_state.turn,
            year=initial_state.year,
            quarter=initial_state.quarter,
            state_json=initial_state.model_dump_json(),
            summary_json=TurnSummary(
                turn=initial_state.turn,
                year=initial_state.year,
                quarter=initial_state.quarter,
                narrative=f"游戏开始！你已加入{company_name}，准备在手机行业大展拳脚。",
            ).model_dump_json(),
        )
        db.add(turn_model)

        # Generate and persist initial events (RSS-driven hybrid mode)
        events = await self.event_generator.roll_events_rss(initial_state, config.difficulty)
        news = self.event_generator.generate_news_for_events(events, initial_state)
        await self.intel_service.save_events(db, game_id, events)
        await self.intel_service.save_news(db, game_id, news)

        await db.flush()

        logger.info("Game created", game_id=game_id, company=config.company_id)

        return GameSessionResponse(
            id=game_id,
            status="active",
            config=config,
            current_turn=initial_state.turn,
            current_year=initial_state.year,
            current_quarter=initial_state.quarter,
            created_at=datetime.now(timezone.utc),
        )

    async def get_game(self, db: AsyncSession, game_id: str) -> GameSessionResponse | None:
        """Retrieve a game session."""
        result = await db.execute(
            select(GameSessionModel).where(GameSessionModel.id == game_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        config = GameConfig.model_validate_json(model.config_json)
        return GameSessionResponse(
            id=model.id,
            status=model.status,
            config=config,
            current_turn=model.current_turn,
            current_year=model.current_year,
            current_quarter=model.current_quarter,
            created_at=model.created_at,
        )

    async def get_world_state(self, db: AsyncSession, game_id: str) -> WorldState | None:
        """Get the current world state for a game."""
        result = await db.execute(
            select(GameSessionModel).where(GameSessionModel.id == game_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None

        # Get latest snapshot
        snap_result = await db.execute(
            select(WorldSnapshotModel)
            .where(WorldSnapshotModel.game_id == game_id)
            .order_by(WorldSnapshotModel.turn.desc())
            .limit(1)
        )
        snapshot = snap_result.scalar_one_or_none()
        if not snapshot:
            return None

        return WorldState.model_validate_json(snapshot.state_json)

    async def get_market_activity(
        self, db: AsyncSession, game_id: str
    ) -> MarketActivitySnapshot:
        """Generate a simulated real-time market activity snapshot."""
        state = await self.get_world_state(db, game_id)
        if not state:
            return MarketActivitySnapshot()

        game_result = await db.execute(
            select(GameSessionModel).where(GameSessionModel.id == game_id)
        )
        game_model = game_result.scalar_one()
        config = GameConfig.model_validate_json(game_model.config_json)
        company_name = self.get_company_name(config.company_id)

        # Generate simulated real-time transactions
        now = time.time()
        brands_pool = [
            "Apple", "Samsung", "Huawei", "OPPO", "vivo",
            "Xiaomi", "Honor", "Nothing", "Google", "OnePlus",
        ]
        segments = [
            ("旗舰", 5000, 12000),
            ("中端", 2000, 5000),
            ("入门", 500, 2000),
        ]
        actions = ["buy", "buy", "buy", "browse", "browse", "switch"]
        reasons_buy = [
            "换新机", "性价比好", "拍照强", "品牌忠诚",
            "朋友推荐", "广告吸引", "配置需要", "颜值高",
        ]
        reasons_switch = [
            "对手更便宜", "对手拍照更好", "系统更流畅",
            "生态更丰富", "售后服务差", "质量投诉",
        ]

        activities = []
        bm = state.brand_metrics
        # Number of ticks based on market activity level
        tick_count = random.randint(8, 15)
        for i in range(tick_count):
            brand = random.choice(brands_pool)
            action = random.choice(actions)
            seg_name, seg_low, seg_high = random.choice(segments)
            price = round(random.uniform(seg_low, seg_high), -2)
            reason = (
                random.choice(reasons_buy) if action == "buy"
                else random.choice(reasons_switch)
            )

            activities.append(MarketActivity(
                timestamp=now - random.uniform(0, 120),  # last 2 minutes
                brand=brand,
                action=action,
                product_segment=seg_name,
                price=price,
                quantity=random.randint(1, 3) if action == "buy" else 0,
                reason=reason,
            ))

        # Sort by timestamp descending (newest first)
        activities.sort(key=lambda a: a.timestamp, reverse=True)

        # Determine market trend
        growth = state.market_metrics.growth_rate
        if growth > 0.01:
            trend = "rising"
        elif growth < -0.01:
            trend = "declining"
        else:
            trend = "stable"

        # Top sellers based on market share
        top_sellers = [
            {"brand": b["name"], "units": b["share"], "trend": random.choice(["up", "down", "stable"])}
            for b in state.market_metrics.top_brands[:5]
        ]

        return MarketActivitySnapshot(
            company_name=company_name,
            activities=activities,
            total_sales_this_quarter=bm.sales_volume,
            total_revenue_this_quarter=bm.revenue,
            market_trend=trend,
            top_sellers=top_sellers,
        )

    async def advance_turn(
        self,
        db: AsyncSession,
        game_id: str,
        decisions: list,
        sim_results: list,
        board_result=None,
    ) -> TurnSummary:
        """Advance the game to the next turn."""
        # Get current state
        current_state = await self.get_world_state(db, game_id)
        if not current_state:
            raise ValueError(f"Game {game_id} not found")

        # Get game config
        game_result = await db.execute(
            select(GameSessionModel).where(GameSessionModel.id == game_id)
        )
        game_model = game_result.scalar_one()
        config = GameConfig.model_validate_json(game_model.config_json)

        # Generate new events (RSS-driven hybrid mode)
        events = await self.event_generator.roll_events_rss(current_state, config.difficulty)

        # Persist events
        news = self.event_generator.generate_news_for_events(events, current_state)
        await self.intel_service.save_events(db, game_id, events)
        await self.intel_service.save_news(db, game_id, news)

        # Apply state transition
        new_state, delta = self.state_machine.apply(
            current_state, decisions, events, sim_results, board_result
        )

        # Persist
        game_model.current_turn = new_state.turn
        game_model.current_year = new_state.year
        game_model.current_quarter = new_state.quarter

        snapshot = WorldSnapshotModel(
            id=str(uuid.uuid4()),
            game_id=game_id,
            turn=new_state.turn,
            state_json=new_state.model_dump_json(),
            delta_json=delta.model_dump_json(),
        )
        db.add(snapshot)

        # Generate narrative summary
        company_name = self.get_company_name(config.company_id)
        summary = TurnSummary(
            turn=new_state.turn,
            year=new_state.year,
            quarter=new_state.quarter,
            events_this_turn=[e.title for e in events],
            decisions_made=[d.action[:50] for d in decisions],
            metrics_delta={
                k: v.delta for k, v in delta.metric_changes.items()
            },
            narrative=f"第{new_state.turn}回合结束。{company_name}继续在手机行业奋战。"
        )

        turn_model = TurnModel(
            id=str(uuid.uuid4()),
            game_id=game_id,
            turn_number=new_state.turn,
            year=new_state.year,
            quarter=new_state.quarter,
            state_json=new_state.model_dump_json(),
            summary_json=summary.model_dump_json(),
        )
        db.add(turn_model)

        await db.flush()
        logger.info("Turn advanced", game_id=game_id, turn=new_state.turn)

        return summary
