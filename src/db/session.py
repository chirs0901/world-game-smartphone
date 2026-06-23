"""Database session management."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./world_game.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Create and yield an async session, auto-commit on success."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables (development convenience; use Alembic in production)."""
    from src.models.base import Base
    # Import all models so they are registered with Base.metadata
    import src.models.game  # noqa: F401
    import src.models.okr  # noqa: F401
    import src.models.intel  # noqa: F401
    import src.models.board  # noqa: F401
    import src.models.simulation  # noqa: F401
    import src.models.world  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
