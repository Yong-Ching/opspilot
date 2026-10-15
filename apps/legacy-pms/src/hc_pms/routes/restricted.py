from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from hc_pms import outbox
from hc_pms.legacy import fail, legacy_row, ok
from hc_pms.portfolio import is_restricted
from hc_pms.routes import DB

router = APIRouter(tags=["restricted list"])

COLUMNS = """r.entry_id, r.security_id, s.sec_name, r.reason, r.added_by, r.added_at,
    r.removed_at"""


class AddIn(BaseModel):
    security_id: str
    reason: str = Field(min_length=5)
    user_id: str


class RemoveIn(BaseModel):
    user_id: str


def _is_compliance(conn: DB, user_id: str) -> bool:
    row = conn.execute("SELECT role FROM users WHERE user_id = %s", (user_id,)).fetchone()
    return row is not None and row["role"] == "COMPLIANCE"


@router.get("/restricted-list")
def list_restricted(conn: DB, include_removed: str = "N") -> dict[str, Any]:
    if include_removed not in ("Y", "N"):
        return fail("ERR_INVALID_FLAG", "include_removed must be Y or N")
    clause = "" if include_removed == "Y" else "WHERE r.removed_at IS NULL"
    rows = conn.execute(
        f"SELECT {COLUMNS} FROM restricted_list r JOIN securities s USING (security_id) "
        f"{clause} ORDER BY r.added_at DESC"
    ).fetchall()
    return ok([legacy_row(r) for r in rows])


@router.get("/restricted-list/check")
def check_restricted(security_id: str, conn: DB) -> dict[str, Any]:
    hit = is_restricted(conn, security_id)
    # Deliberately does NOT return the reason: restriction reasons can themselves be MNPI.
    return ok({"security_id": security_id, "restricted": "Y" if hit else "N"})


@router.post("/restricted-list")
def add_restricted(body: AddIn, conn: DB) -> dict[str, Any]:
    if not _is_compliance(conn, body.user_id):
        return fail("ERR_NOT_AUTHORISED", "Only compliance can change the restricted list")
    if (
        conn.execute(
            "SELECT 1 FROM securities WHERE security_id = %s", (body.security_id,)
        ).fetchone()
        is None
    ):
        return fail("ERR_SECURITY_NOT_FOUND", f"No security {body.security_id}")
    if is_restricted(conn, body.security_id):
        return fail("ERR_ALREADY_RESTRICTED", "Security is already restricted")
    row = conn.execute(
        "INSERT INTO restricted_list (security_id, reason, added_by) VALUES (%s, %s, %s) "
        "RETURNING *",
        (body.security_id, body.reason, body.user_id),
    ).fetchone()
    assert row is not None
    data = legacy_row(row)
    outbox.record_event(conn, "restricted_list.updated", str(row["entry_id"]),
                        {"action": "ADDED", **data})  # fmt: skip
    return ok(data)


@router.post("/restricted-list/{entry_id}/remove")
def remove_restricted(entry_id: int, body: RemoveIn, conn: DB) -> dict[str, Any]:
    if not _is_compliance(conn, body.user_id):
        return fail("ERR_NOT_AUTHORISED", "Only compliance can change the restricted list")
    row = conn.execute(
        "UPDATE restricted_list SET removed_at = now() WHERE entry_id = %s AND removed_at IS NULL "
        "RETURNING *",
        (entry_id,),
    ).fetchone()
    if row is None:
        return fail("ERR_ENTRY_NOT_FOUND", f"No active entry {entry_id}")
    data = legacy_row(row)
    outbox.record_event(conn, "restricted_list.updated", str(entry_id),
                        {"action": "REMOVED", **data})  # fmt: skip
    return ok(data)
