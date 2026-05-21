from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base
from app.db.engine import engine, normalize_database_url
import app.models  # noqa: F401 - registers all tables in Base.metadata


REQUIRED_TABLES = {"tasks", "telegram_conversations"}


async def initialize_database() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        existing_tables = await conn.run_sync(_table_names)

    if _should_run_alembic(existing_tables):
        try:
            await asyncio.to_thread(_run_alembic_upgrade)
            logger.info("  database : alembic upgrade head completed")
        except Exception as exc:
            logger.warning(
                "  database : alembic upgrade head failed, using metadata fallback - %s",
                exc,
            )
    else:
        logger.info("  database : alembic skipped for existing unversioned schema")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_task_claiming_columns(conn)
        existing_tables = await conn.run_sync(_table_names)

    missing_tables = sorted(REQUIRED_TABLES - existing_tables)
    if missing_tables:
        raise RuntimeError(
            "database initialization incomplete; missing tables: "
            + ", ".join(missing_tables)
        )

    logger.info("  database : initialized")


def _should_run_alembic(existing_tables: set[str]) -> bool:
    if "alembic_version" in existing_tables:
        return True
    return not (existing_tables & REQUIRED_TABLES)


def _table_names(connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def _run_alembic_upgrade() -> None:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", _alembic_config_url())
    command.upgrade(config, "head")


def _alembic_config_url() -> str:
    return normalize_database_url(settings.DATABASE_URL).replace("%", "%%")


async def _ensure_task_claiming_columns(conn) -> None:
    await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS runner_id VARCHAR(100)"))
    await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS runtime_id VARCHAR(100)"))
    await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE"))
    await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS claim_state VARCHAR(50)"))
    await conn.execute(
        text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS claim_attempts INTEGER NOT NULL DEFAULT 0")
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_tasks_claiming_status_claimed_at "
            "ON tasks (status, claimed_at)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_tasks_claiming_runtime_state "
            "ON tasks (runtime_id, claim_state)"
        )
    )
