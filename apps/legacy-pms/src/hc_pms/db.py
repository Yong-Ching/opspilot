from collections.abc import Iterator
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

Conn = Connection[dict[str, Any]]

_pool: ConnectionPool[Conn] | None = None


def open_pool(url: str) -> None:
    global _pool
    _pool = ConnectionPool(
        url,
        connection_class=Connection[dict[str, Any]],
        kwargs={"row_factory": dict_row},
        open=True,
    )
    _pool.wait()


def close_pool() -> None:
    if _pool is not None:
        _pool.close()


def get_conn() -> Iterator[Conn]:
    """One connection + one transaction per request: commits on success, rolls back on error."""
    assert _pool is not None, "pool not opened"
    with _pool.connection() as conn:
        yield conn
