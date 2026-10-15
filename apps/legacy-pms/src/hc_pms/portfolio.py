"""Holdings and valuation, shared by several endpoints."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from hc_pms.db import Conn


@dataclass
class Position:
    security_id: str
    sec_name: str
    sec_type: str
    sector: str
    currency: str
    quantity: int
    px_minor: int  # cents, security currency
    px_date: date
    fx_rate: Decimal
    mv_sgd: Decimal


def positions(conn: Conn, fund_code: str, as_of: date) -> list[Position]:
    rows = conn.execute(
        """
        WITH pos AS (
            SELECT security_id,
                   sum(CASE txn_type WHEN 'BUY' THEN quantity
                                     WHEN 'SELL' THEN -quantity ELSE 0 END)::bigint AS quantity
            FROM transactions WHERE fund_code = %(f)s AND trade_date <= %(d)s
            GROUP BY security_id
        )
        SELECT s.security_id, s.sec_name, s.sec_type, s.sector, s.currency, pos.quantity,
               px.px_close_minor, px.px_date,
               CASE WHEN s.currency = 'SGD' THEN 1 ELSE fx.rate_to_sgd END AS fx_rate
        FROM pos
        JOIN securities s USING (security_id)
        JOIN LATERAL (SELECT px_close_minor, px_date FROM prices p
                      WHERE p.security_id = pos.security_id AND p.px_date <= %(d)s
                      ORDER BY px_date DESC LIMIT 1) px ON TRUE
        LEFT JOIN LATERAL (SELECT rate_to_sgd FROM fx_rates x
                           WHERE x.ccy = s.currency AND x.fx_date <= %(d)s
                           ORDER BY fx_date DESC LIMIT 1) fx ON TRUE
        WHERE pos.quantity <> 0
        """,
        {"f": fund_code, "d": as_of},
    ).fetchall()
    out = []
    for r in rows:
        mv = Decimal(r["quantity"]) * Decimal(r["px_close_minor"]) / 100 * Decimal(r["fx_rate"])
        out.append(
            Position(
                security_id=r["security_id"],
                sec_name=r["sec_name"],
                sec_type=r["sec_type"],
                sector=r["sector"],
                currency=r["currency"],
                quantity=r["quantity"],
                px_minor=r["px_close_minor"],
                px_date=r["px_date"],
                fx_rate=Decimal(r["fx_rate"]),
                mv_sgd=mv.quantize(Decimal("0.01")),
            )
        )
    return sorted(out, key=lambda p: p.mv_sgd, reverse=True)


def cash(conn: Conn, fund_code: str, as_of: date) -> Decimal:
    row = conn.execute(
        """SELECT (SELECT coalesce(sum(amount_sgd), 0) FROM cash_flows
                   WHERE fund_code = %(f)s AND flow_date <= %(d)s)
                + (SELECT coalesce(sum(amount_sgd), 0) FROM transactions
                   WHERE fund_code = %(f)s AND trade_date <= %(d)s) AS cash""",
        {"f": fund_code, "d": as_of},
    ).fetchone()
    return Decimal(row["cash"]) if row else Decimal(0)


def valuation(conn: Conn, fund_code: str, as_of: date) -> dict[str, Any]:
    pos = positions(conn, fund_code, as_of)
    cash_sgd = cash(conn, fund_code, as_of)
    nav = sum((p.mv_sgd for p in pos), Decimal(0)) + cash_sgd
    return {"positions": pos, "cash_sgd": cash_sgd, "nav_sgd": nav}


def is_restricted(conn: Conn, security_id: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT entry_id, reason, added_at FROM restricted_list "
        "WHERE security_id = %s AND removed_at IS NULL",
        (security_id,),
    ).fetchone()
