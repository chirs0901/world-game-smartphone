"""API route aggregation."""

from fastapi import APIRouter

from src.api.game import router as game_router
from src.api.okr import router as okr_router
from src.api.intel import router as intel_router
from src.api.board import router as board_router
from src.api.rss import router as rss_router
from src.api.rss_intel import router as rss_intel_router
from src.api.simulation import router as simulation_router
from src.api.social import router as social_router
from src.api.tech_roadmap import router as tech_router
from src.api.phones import router as phones_router
from src.api.world import router as world_router
from src.api.engine_api import router as engine_router

api_router = APIRouter()

api_router.include_router(game_router, prefix="/game", tags=["Game"])
api_router.include_router(okr_router, tags=["OKR"])
api_router.include_router(intel_router, tags=["Intel"])
api_router.include_router(board_router, tags=["Board"])
api_router.include_router(rss_router, tags=["RSS"])
api_router.include_router(rss_intel_router, tags=["RSS Intelligence"])
api_router.include_router(simulation_router, tags=["Simulation"])
api_router.include_router(social_router, tags=["Social"])
api_router.include_router(tech_router, tags=["TechRoadmap"])
api_router.include_router(phones_router, tags=["Phones"])
api_router.include_router(world_router, tags=["World"])
api_router.include_router(engine_router, tags=["Engine"])
