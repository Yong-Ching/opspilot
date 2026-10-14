from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from psycopg import sql
from pydantic import BaseModel, Field

from acme_oms import outbox
from acme_oms.auth import require_api_key
from acme_oms.config import settings
from acme_oms.db import Conn, get_conn
from acme_oms.legacy import fail, legacy_row, ok, parse_date

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])
DB = Annotated[Conn, Depends(get_conn)]

ORDER_STATUSES = {
    "created", "approved", "invoiced", "processing",
    "shipped", "delivered", "unavailable", "canceled",
}  # fmt: skip
REFUNDABLE_STATUSES = {"shipped", "delivered", "canceled"}


def _order_detail(conn: Conn, order_id: str) -> dict[str, Any] | None:
    order = conn.execute(
        """SELECT o.*, c.customer_unique_id, c.customer_city, c.customer_state
           FROM orders o JOIN customers c USING (customer_id)
           WHERE o.order_id = %s""",
        (order_id,),
    ).fetchone()
    if order is None:
        return None
    items = conn.execute(
        """SELECT i.order_item_id, i.product_id, p.product_category_name, i.seller_id,
                  i.price, i.freight_value, i.shipping_limit_date
           FROM order_items i LEFT JOIN products p USING (product_id)
           WHERE i.order_id = %s ORDER BY i.order_item_id""",
        (order_id,),
    ).fetchall()
    payments = conn.execute(
        "SELECT payment_sequential, payment_type, payment_installments, payment_value "
        "FROM order_payments WHERE order_id = %s ORDER BY payment_sequential",
        (order_id,),
    ).fetchall()
    reviews = conn.execute(
        "SELECT review_score, review_comment_title, review_comment_message, review_creation_date "
        "FROM order_reviews WHERE order_id = %s",
        (order_id,),
    ).fetchall()
    refunds = conn.execute(
        "SELECT * FROM refund_requests WHERE order_id = %s ORDER BY refund_id", (order_id,)
    ).fetchall()
    return {
        **legacy_row(order),
        "items": [legacy_row(r) for r in items],
        "payments": [legacy_row(r) for r in payments],
        "reviews": [legacy_row(r) for r in reviews],
        "refunds": [legacy_row(r) for r in refunds],
    }


@router.get("/orders/{order_id}")
def get_order(order_id: str, conn: DB) -> dict[str, Any]:
    detail = _order_detail(conn, order_id)
    if detail is None:
        return fail("ORDER_NOT_FOUND", f"Pedido {order_id} nao encontrado")
    return ok(detail)


@router.get("/orders")
def search_orders(
    conn: DB,
    customer_id: str | None = None,
    status: str | None = None,
    dt_from: Annotated[str | None, Query(description="DD/MM/YYYY")] = None,
    dt_to: Annotated[str | None, Query(description="DD/MM/YYYY")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1)] = 20,
) -> dict[str, Any]:
    per_page = min(per_page, settings.max_page_size)  # silently capped (legacy quirk)
    where: list[sql.Composable] = []
    params: list[Any] = []
    if customer_id:
        where.append(sql.SQL("customer_id = %s"))
        params.append(customer_id)
    if status:
        where.append(sql.SQL("order_status = %s"))
        params.append(status)
    try:
        if dt_from:
            where.append(sql.SQL("order_purchase_timestamp >= %s"))
            params.append(parse_date(dt_from))
        if dt_to:
            where.append(sql.SQL("order_purchase_timestamp < %s::timestamp + interval '1 day'"))
            params.append(parse_date(dt_to))
    except ValueError:
        return fail("INVALID_DATE", "Use o formato DD/MM/YYYY")
    clause = sql.SQL("WHERE {}").format(sql.SQL(" AND ").join(where)) if where else sql.SQL("")
    total = conn.execute(
        sql.SQL("SELECT count(*) AS n FROM orders {}").format(clause), params
    ).fetchone()
    rows = conn.execute(
        sql.SQL(
            "SELECT * FROM orders {} ORDER BY order_purchase_timestamp DESC LIMIT %s OFFSET %s"
        ).format(clause),
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()
    paging = {"page": page, "per_page": per_page, "total": total["n"] if total else 0}
    return ok([legacy_row(r) for r in rows], paging)


@router.get("/customers/{customer_unique_id}/orders")
def customer_history(customer_unique_id: str, conn: DB) -> dict[str, Any]:
    rows = conn.execute(
        """SELECT o.order_id, o.order_status, o.order_purchase_timestamp,
                  o.order_delivered_customer_date, o.order_estimated_delivery_date,
                  (SELECT sum(payment_value) FROM order_payments p
                   WHERE p.order_id = o.order_id) AS total_paid
           FROM orders o JOIN customers c USING (customer_id)
           WHERE c.customer_unique_id = %s
           ORDER BY o.order_purchase_timestamp DESC""",
        (customer_unique_id,),
    ).fetchall()
    if not rows:
        return fail("CUSTOMER_NOT_FOUND", f"Cliente {customer_unique_id} nao encontrado")
    return ok([legacy_row(r) for r in rows])


class RefundIn(BaseModel):
    order_id: str
    amount: Decimal = Field(gt=0, decimal_places=2)
    reason: str = Field(min_length=3, max_length=1000)
    requested_by: str = Field(min_length=1)


@router.post("/refunds")
def create_refund(body: RefundIn, conn: DB) -> dict[str, Any]:
    order = conn.execute(
        "SELECT order_status FROM orders WHERE order_id = %s FOR UPDATE", (body.order_id,)
    ).fetchone()
    if order is None:
        return fail("ORDER_NOT_FOUND", f"Pedido {body.order_id} nao encontrado")
    if order["order_status"] not in REFUNDABLE_STATUSES:
        return fail("REFUND_NOT_ALLOWED", f"Status {order['order_status']} nao permite reembolso")
    totals = conn.execute(
        """SELECT
             (SELECT coalesce(sum(payment_value), 0) FROM order_payments WHERE order_id = %(o)s)
               AS paid,
             (SELECT coalesce(sum(amount), 0) FROM refund_requests
              WHERE order_id = %(o)s AND status <> 'REJECTED') AS refunded""",
        {"o": body.order_id},
    ).fetchone()
    assert totals is not None
    remaining: Decimal = totals["paid"] - totals["refunded"]
    if body.amount > remaining:
        return fail("REFUND_EXCEEDS_PAID", f"Valor maximo para reembolso: {remaining}")
    refund = conn.execute(
        """INSERT INTO refund_requests (order_id, amount, reason, requested_by)
           VALUES (%s, %s, %s, %s) RETURNING *""",
        (body.order_id, body.amount, body.reason, body.requested_by),
    ).fetchone()
    assert refund is not None
    data = legacy_row(refund)
    outbox.record_event(conn, "refund.requested", str(refund["refund_id"]), data)
    return ok(data)


@router.get("/refunds/{refund_id}")
def get_refund(refund_id: int, conn: DB) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM refund_requests WHERE refund_id = %s", (refund_id,)
    ).fetchone()
    if row is None:
        return fail("REFUND_NOT_FOUND", f"Reembolso {refund_id} nao encontrado")
    return ok(legacy_row(row))


class StatusIn(BaseModel):
    status: str


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: str, body: StatusIn, conn: DB) -> dict[str, Any]:
    if body.status not in ORDER_STATUSES:
        return fail("INVALID_STATUS", f"Status invalido: {body.status}")
    row = conn.execute(
        "UPDATE orders SET order_status = %s WHERE order_id = %s RETURNING order_id, order_status",
        (body.status, order_id),
    ).fetchone()
    if row is None:
        return fail("ORDER_NOT_FOUND", f"Pedido {order_id} nao encontrado")
    outbox.record_event(conn, "order.updated", order_id, dict(row))
    return ok(dict(row))
