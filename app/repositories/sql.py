from contextlib import contextmanager
from typing import Iterator

from psycopg_pool import ConnectionPool

from app.core.config import settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(settings.database_url, open=False)
        _pool.open()
    return _pool


@contextmanager
def get_connection() -> Iterator:
    with get_pool().connection() as conn:
        yield conn

