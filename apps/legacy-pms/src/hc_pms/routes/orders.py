from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from hc_pms import outbox
from hc_pms.config import settings
from hc_pms.legacy import fail, legacy_row, ok
from hc_pms.portfolio import cash, is_restricted, positions
from hc_pms.routes import DB

router = APIRouter(tags=["orders"])
FEE_RATE = Decimal("0.001")
MIN_FEE = Decimal(25)


class ProposeIn(BaseModel):
    fund_code: str
    security_id: str
    side: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0, description="major units, security ccy")
    rationale: str = Field(min_length=10, max_length=4000)
    proposed_by: str = Field(description="user_id; the PMS trusts the caller (legacy)")


class DecisionIn(BaseModel):
    user_id: str
    note: str | None = Field(default=None, max_length=2000)


def _user(conn: DB, user_id: str) -> dict[str, Any] | None:
    return conn.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()


def _held(conn: DB, fund_code: str, security_id: str) -> int:
    return next(
        (
            p.quantity
            for p in positions(conn, fund_code, date.today())
            if p.security_id == security_id
        ),
        0,
    )


def _order(conn: DB, order_id: int, lock: bool = False) -> dict[str, Any] | None:
    q = "SELECT * FROM orders WHERE order_id = %s" + (" FOR UPDATE" if lock else "")
    return conn.execute(q, (order_id,)).fetchone()  # type: ignore[arg-type]


@router.get("/orders")
def list_orders(
    conn: DB,
    fund_code: str | None = None,
    status: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1)] = 20,
) -> dict[str, Any]:
    per_page = min(per_page, settings.max_page_size)
    params = {"f": fund_code, "s": status, "lim": per_page, "off": (page - 1) * per_page}
    where = "(%(f)s::text IS NULL OR fund_code = %(f)s) AND (%(s)s::text IS NULL OR status = %(s)s)"
    total = conn.execute(f"SELECT count(*) AS n FROM orders WHERE {where}", params).fetchone()
    rows = conn.execute(
        f"SELECT * FROM orders WHERE {where} ORDER BY order_id DESC LIMIT %(lim)s OFFSET %(off)s",
        params,
    ).fetchall()
    paging = {"page": page, "per_page": per_page, "total": total["n"] if total else 0}
    return ok([legacy_row(r) for r in rows], paging)


@router.get("/orders/{order_id}")
def get_order(order_id: int, conn: DB) -> dict[str, Any]:
    row = _order(conn, order_id)
    if row is None:
        return fail("ERR_ORDER_NOT_FOUND", f"No order {order_id}")
    return ok(legacy_row(row))


@router.post("/orders")
def propose_order(body: ProposeIn, conn: DB) -> dict[str, Any]:
    if (
        conn.execute("SELECT 1 FROM funds WHERE fund_code = %s", (body.fund_code,)).fetchone()
        is None
    ):
        return fail("ERR_FUND_NOT_FOUND", f"No fund {body.fund_code}")
    sec = conn.execute(
        "SELECT board_lot FROM securities WHERE security_id = %s", (body.security_id,)
    ).fetchone()
    if sec is None:
        return fail("ERR_SECURITY_NOT_FOUND", f"No security {body.security_id}")
    user = _user(conn, body.proposed_by)
    if user is None or user["role"] not in ("ANALYST", "PM"):
        return fail("ERR_NOT_AUTHORISED", "Only analysts and PMs can propose orders")
    if body.quantity % sec["board_lot"]:
        return fail("ERR_BOARD_LOT", f"Quantity must be a multiple of {sec['board_lot']}")
    if is_restricted(conn, body.security_id):
        return fail("ERR_RESTRICTED", "Security is on the restricted list")
    if body.side == "SELL" and _held(conn, body.fund_code, body.security_id) < body.quantity:
        return fail("ERR_INSUFFICIENT_HOLDING", "Cannot sell more than the fund holds")
    row = conn.execute(
        """INSERT INTO orders (fund_code, security_id, side, quantity, limit_price, rationale,
                               proposed_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
        (body.fund_code, body.security_id, body.side, body.quantity, body.limit_price,
         body.rationale, body.proposed_by),
    ).fetchone()  # fmt: skip
    assert row is not None
    data = legacy_row(row)
    outbox.record_event(conn, "order.proposed", str(row["order_id"]), data)
    return ok(data)


@router.post("/orders/{order_id}/approve")
def approve_order(order_id: int, body: DecisionIn, conn: DB) -> dict[str, Any]:
    order = _order(conn, order_id, lock=True)
    if order is None:
        return fail("ERR_ORDER_NOT_FOUND", f"No order {order_id}")
    if order["status"] != "PROPOSED":
        return fail("ERR_INVALID_STATE", f"Order is {order['status']}")
    fund = conn.execute("SELECT pm_user_id FROM funds WHERE fund_code = %s", (order["fund_code"],))
    pm = fund.fetchone()
    if pm is None or pm["pm_user_id"] != body.user_id:
        return fail("ERR_NOT_AUTHORISED", "Only the fund's PM can approve")
    if body.user_id == order["proposed_by"]:
        return fail("ERR_FOUR_EYES", "Approver must be different from proposer")
    if is_restricted(conn, order["security_id"]):
        return fail("ERR_RESTRICTED", "Security was restricted after the order was proposed")
    row = conn.execute(
        "UPDATE orders SET status = 'APPROVED', decided_by = %s, decided_at = now(), "
        "decision_note = %s WHERE order_id = %s RETURNING *",
        (body.user_id, body.note, order_id),
    ).fetchone()
    assert row is not None
    data = legacy_row(row)
    outbox.record_event(conn, "order.approved", str(order_id), data)
    return ok(data)


@router.post("/orders/{order_id}/reject")
def reject_order(order_id: int, body: DecisionIn, conn: DB) -> dict[str, Any]:
    order = _order(conn, order_id, lock=True)
    if order is None:
        return fail("ERR_ORDER_NOT_FOUND", f"No order {order_id}")
    if order["status"] != "PROPOSED":
        return fail("ERR_INVALID_STATE", f"Order is {order['status']}")
    if not body.note:
        return fail("ERR_NOTE_REQUIRED", "A rejection needs a note")
    user = _user(conn, body.user_id)
    pm = conn.execute(
        "SELECT pm_user_id FROM funds WHERE fund_code = %s", (order["fund_code"],)
    ).fetchone()
    allowed = user is not None and (
        user["role"] == "COMPLIANCE" or (pm is not None and pm["pm_user_id"] == body.user_id)
    )
    if not allowed:
        return fail("ERR_NOT_AUTHORISED", "Only the fund's PM or compliance can reject")
    row = conn.execute(
        "UPDATE orders SET status = 'REJECTED', decided_by = %s, decided_at = now(), "
        "decision_note = %s WHERE order_id = %s RETURNING *",
        (body.user_id, body.note, order_id),
    ).fetchone()
    assert row is not None
    data = legacy_row(row)
    outbox.record_event(conn, "order.rejected", str(order_id), data)
    return ok(data)


@router.post("/orders/{order_id}/execute")
def execute_order(order_id: int, conn: DB) -> dict[str, Any]:
    """Simulates the dealing desk: fills at the latest close."""
    order = _order(conn, order_id, lock=True)
    if order is None:
        return fail("ERR_ORDER_NOT_FOUND", f"No order {order_id}")
    if order["status"] != "APPROVED":
        return fail("ERR_INVALID_STATE", f"Order is {order['status']}")
    q = conn.execute(
        """SELECT p.px_close_minor, s.currency,
                  CASE WHEN s.currency = 'SGD' THEN 1 ELSE
                    (SELECT rate_to_sgd FROM fx_rates x WHERE x.ccy = s.currency
                     ORDER BY fx_date DESC LIMIT 1) END AS fx
           FROM securities s JOIN LATERAL (
             SELECT px_close_minor FROM prices WHERE security_id = s.security_id
             ORDER BY px_date DESC LIMIT 1) p ON TRUE
           WHERE s.security_id = %s""",
        (order["security_id"],),
    ).fetchone()
    assert q is not None
    price = Decimal(q["px_close_minor"]) / 100
    limit = order["limit_price"]
    if limit is not None and (
        (order["side"] == "BUY" and price > limit) or (order["side"] == "SELL" and price < limit)
    ):
        return fail("ERR_LIMIT_NOT_MET", f"Market {price} vs limit {limit}")
    fx = Decimal(q["fx"])
    notional = (order["quantity"] * price * fx).quantize(Decimal("0.01"))
    fees = max((notional * FEE_RATE).quantize(Decimal("0.01")), MIN_FEE)
    today = date.today()
    if order["side"] == "BUY":
        if cash(conn, order["fund_code"], today) < notional + fees:
            return fail("ERR_INSUFFICIENT_CASH", "Not enough cash in the fund")
        amount = -(notional + fees)
    else:
        if _held(conn, order["fund_code"], order["security_id"]) < order["quantity"]:
            return fail("ERR_INSUFFICIENT_HOLDING", "Cannot sell more than the fund holds")
        amount = notional - fees
    txn = conn.execute(
        """INSERT INTO transactions (fund_code, security_id, trade_date, settle_date, txn_type,
                                     quantity, price, fx_rate, fees_sgd, amount_sgd, order_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING txn_id""",
        (order["fund_code"], order["security_id"], today, today + timedelta(days=2),
         order["side"], order["quantity"], price, fx, fees, amount, order_id),
    ).fetchone()  # fmt: skip
    row = conn.execute(
        "UPDATE orders SET status = 'EXECUTED' WHERE order_id = %s RETURNING *", (order_id,)
    ).fetchone()
    assert row is not None and txn is not None
    data = legacy_row({**row, "txn_id": txn["txn_id"], "fill_price": price, "amount_sgd": amount})
    outbox.record_event(conn, "order.executed", str(order_id), data)
    return ok(data)
