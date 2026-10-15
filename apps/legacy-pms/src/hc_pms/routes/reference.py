from typing import Annotated, Any

from fastapi import APIRouter, Query

from hc_pms.config import settings
from hc_pms.legacy import fail, legacy_row, ok, parse_date
from hc_pms.routes import DB

router = APIRouter(tags=["reference"])

SECURITY_COLUMNS = """s.security_id, s.sec_name, s.sec_type, s.sector, s.currency, s.board_lot,
    s.sponsor,
    (SELECT id_value FROM security_identifiers i
     WHERE i.security_id = s.security_id AND i.id_type = 'SGX' AND i.is_current) AS sgx_code"""


@router.get("/users")
def list_users(conn: DB) -> dict[str, Any]:
    return ok(conn.execute("SELECT * FROM users ORDER BY role, user_id").fetchall())


@router.get("/securities")
def list_securities(conn: DB) -> dict[str, Any]:
    rows = conn.execute(f"SELECT {SECURITY_COLUMNS} FROM securities s ORDER BY s.security_id")
    return ok([legacy_row(r) for r in rows.fetchall()])


@router.get("/securities/lookup")
def lookup_security(code: str, conn: DB) -> dict[str, Any]:
    """Find a security by SGX code or Yahoo ticker, including retired codes."""
    row = conn.execute(
        "SELECT security_id, id_type, id_value, is_current FROM security_identifiers "
        "WHERE upper(id_value) = upper(%s)",
        (code,),
    ).fetchone()
    if row is None:
        return fail("ERR_SECURITY_NOT_FOUND", f"No security with code {code}")
    sec = conn.execute(
        f"SELECT {SECURITY_COLUMNS} FROM securities s WHERE s.security_id = %s",
        (row["security_id"],),
    ).fetchone()
    return ok(legacy_row({**(sec or {}), "matched_code": row["id_value"],
                          "matched_code_current": row["is_current"]}))  # fmt: skip


@router.get("/securities/{security_id}")
def get_security(security_id: str, conn: DB) -> dict[str, Any]:
    sec = conn.execute(
        f"SELECT {SECURITY_COLUMNS} FROM securities s WHERE s.security_id = %s", (security_id,)
    ).fetchone()
    if sec is None:
        return fail("ERR_SECURITY_NOT_FOUND", f"No security {security_id}")
    ids = conn.execute(
        "SELECT id_type, id_value, is_current FROM security_identifiers WHERE security_id = %s "
        "ORDER BY id_type, is_current DESC",
        (security_id,),
    ).fetchall()
    last = conn.execute(
        "SELECT px_date, px_close_minor FROM prices WHERE security_id = %s "
        "ORDER BY px_date DESC LIMIT 1",
        (security_id,),
    ).fetchone()
    return ok(legacy_row({**sec, "identifiers": [legacy_row(i) for i in ids],
                          "px_last_minor": last and last["px_close_minor"],
                          "px_last_date": last and last["px_date"]}))  # fmt: skip


@router.get("/securities/{security_id}/prices")
def get_prices(
    security_id: str,
    conn: DB,
    dt_from: Annotated[str | None, Query(description="DD/MM/YYYY")] = None,
    dt_to: Annotated[str | None, Query(description="DD/MM/YYYY")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1)] = 20,
) -> dict[str, Any]:
    per_page = min(per_page, settings.max_page_size)  # silently capped (legacy quirk)
    try:
        lo = parse_date(dt_from) if dt_from else None
        hi = parse_date(dt_to) if dt_to else None
    except ValueError:
        return fail("ERR_INVALID_DATE", "Dates must be DD/MM/YYYY")
    params = {"s": security_id, "lo": lo, "hi": hi}
    where = ("security_id = %(s)s AND (%(lo)s::date IS NULL OR px_date >= %(lo)s) "
             "AND (%(hi)s::date IS NULL OR px_date <= %(hi)s)")  # fmt: skip
    total = conn.execute(f"SELECT count(*) AS n FROM prices WHERE {where}", params).fetchone()
    rows = conn.execute(
        f"SELECT px_date, px_close_minor FROM prices WHERE {where} "
        "ORDER BY px_date DESC LIMIT %(lim)s OFFSET %(off)s",
        {**params, "lim": per_page, "off": (page - 1) * per_page},
    ).fetchall()
    paging = {"page": page, "per_page": per_page, "total": total["n"] if total else 0}
    return ok([legacy_row(r) for r in rows], paging)
