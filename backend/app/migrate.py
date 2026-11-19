from pathlib import Path

from alembic import command
from alembic.config import Config

_ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"


def run_migrations(database_url: str) -> None:
    """Bring the database up to the latest schema (safe to run on every startup)."""
    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.attributes["database_url"] = database_url
    command.upgrade(cfg, "head")
