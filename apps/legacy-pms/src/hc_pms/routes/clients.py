from typing import Annotated, Any

from fastapi import APIRouter, Query

from hc_pms.config import settings
from hc_pms.legacy import fail, legacy_row, ok
from hc_pms.routes import DB

router = APIRouter(tags=["clients"])


@router.get("/clients")
def list_clients(
    conn: DB,
    rm_user_id: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1)] = 20,
) -> dict[str, Any]:
    per_page = min(per_page, settings.max_page_size)
    params = {"rm": rm_user_id, "lim": per_page, "off": (page - 1) * per_page}
    where = "(%(rm)s::text IS NULL OR rm_user_id = %(rm)s)"
    total = conn.execute(f"SELECT count(*) AS n FROM clients WHERE {where}", params).fetchone()
    rows = conn.execute(
        f"SELECT client_id, full_name, risk_profile, rm_user_id FROM clients WHERE {where} "
        "ORDER BY client_id LIMIT %(lim)s OFFSET %(off)s",
        params,
    ).fetchall()
    paging = {"page": page, "per_page": per_page, "total": total["n"] if total else 0}
    return ok(rows, paging)


@router.get("/clients/{client_id}")
def get_client(client_id: str, conn: DB) -> dict[str, Any]:
    # Legacy behaviour: returns the FULL record, including NRIC, to any caller with the API key.
    row = conn.execute("SELECT * FROM clients WHERE client_id = %s", (client_id,)).fetchone()
    if row is None:
        return fail("ERR_CLIENT_NOT_FOUND", f"No client {client_id}")
    mandates = conn.execute(
        "SELECT fund_code, fund_name FROM funds WHERE client_id = %s", (client_id,)
    ).fetchall()
    return ok(legacy_row({**row, "mandates": mandates}))
