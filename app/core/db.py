from pathlib import Path

from app.core.logging import get_logger
from app.repositories.sql import get_connection

logger = get_logger(__name__)


def initialize_database() -> None:
    """Apply idempotent SQL migrations at service startup."""
    root = Path(__file__).resolve().parents[2]
    migrations = [root / "sql" / "001_init.sql", root / "sql" / "002_indexes.sql"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for migration in migrations:
                logger.info("applying_database_migration", extra={"migration": migration.name})
                cur.execute(migration.read_text())
        conn.commit()
