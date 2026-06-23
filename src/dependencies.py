"""FastAPI dependency injection providers."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.engines.rss_intel import RSSIntelEngine
from src.engines.tech_roadmap import TechRoadmapEngine
from src.llm.client import LLMClient
from src.services.board_service import BoardService
from src.services.game_service import GameService
from src.services.intel_service import IntelService
from src.services.okr_service import OKRService
from src.services.rss_service import RSSService
from src.services.simulation_service import SimulationService
from src.services.social_service import SocialService
from src.services.world_service import WorldService

# Singleton service instances (RSS created first for injection into others)
_rss_service = RSSService()
_rss_intel_engine = RSSIntelEngine()
_tech_roadmap_engine = TechRoadmapEngine(rss_service=_rss_service, rss_intel_engine=_rss_intel_engine)
_game_service = GameService(rss_service=_rss_service, rss_intel_engine=_rss_intel_engine)
_okr_service = OKRService()
_intel_service = IntelService()
_board_service = BoardService(llm_client=LLMClient())
_simulation_service = SimulationService(rss_service=_rss_service, rss_intel_engine=_rss_intel_engine)
_world_service = WorldService()
_social_service = SocialService()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with get_session() as session:
        yield session


def get_game_service() -> GameService:
    return _game_service


def get_okr_service() -> OKRService:
    return _okr_service


def get_intel_service() -> IntelService:
    return _intel_service


def get_board_service() -> BoardService:
    return _board_service


def get_simulation_service() -> SimulationService:
    return _simulation_service


def get_world_service() -> WorldService:
    return _world_service


def get_social_service() -> SocialService:
    return _social_service


def get_rss_service() -> RSSService:
    return _rss_service


def get_rss_intel_engine() -> RSSIntelEngine:
    return _rss_intel_engine


def get_tech_roadmap_engine() -> TechRoadmapEngine:
    return _tech_roadmap_engine
