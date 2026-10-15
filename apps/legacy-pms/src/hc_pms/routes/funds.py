from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Query

from hc_pms.config import settings
from hc_pms.legacy import fail, legacy_row, ok, parse_date
from hc_pms.portfolio import valuation
from hc_pms.routes import DB

router = APIRouter(tags=["funds"])


def _as_of(value: str | None) -> date | None:
    return parse_date(value) if value else date.today()


def _fund(conn: DB, fund_code: str) -> dict[str, Any] | None:
    return conn.execute("SELECT * FROM funds WHERE fund_code = %s", (fund_code,)).fetchone()


@router.get("/funds")
def list_funds(conn: DB) -> dict[str, Any]:
    rows = conn.execute("SELECT * FROM funds ORDER BY fund_type DESC, fund_code").fetchall()
    return ok([legacy_row(r) for r in rows])


@router.get("/funds/{fund_code}")
def get_fund(fund_code: str, conn: DB) -> dict[str, Any]:
    fund = _fund(conn, fund_code)
    if fund is None:
        return fail("ERR_FUND_NOT_FOUND", f"No fund {fund_code}")
    return ok(legacy_row(fund))


@router.get("/funds/{fund_code}/holdings")
def holdings(
    fund_code: str, conn: DB, as_of: Annotated[str | None, Query(description="DD/MM/YYYY")] = None
) -> dict[str, Any]:
    if _fund(conn, fund_code) is None:
        return fail("ERR_FUND_NOT_FOUND", f"No fund {fund_code}")
    try:
        d = _as_of(as_of)
    except ValueError:
        return fail("ERR_INVALID_DATE", "Dates must be DD/MM/YYYY")
    assert d is not None
    v = valuation(conn, fund_code, d)
    nav: Decimal = v["nav_sgd"]
    rows = [
        legacy_row(
            {
                "security_id": p.security_id,
                "sec_name": p.sec_name,
                "sec_type": p.sec_type,
                "sector": p.sector,
                "ccy": p.currency,
                "quantity": p.quantity,
                "px_minor": p.px_minor,
                "px_date": p.px_date,
                "fx_rate": p.fx_rate,
                "mv_sgd": p.mv_sgd,
                "weight_pct": round(p.mv_sgd / nav * 100, 2) if nav else 0,
            }
        )  # fmt: skip
        for p in v["positions"]
    ]
    summary = {
        "fund_code": fund_code, "as_of": d.strftime("%d/%m/%Y"), "nav_sgd": float(nav),
        "cash_sgd": float(v["cash_sgd"]),
        "cash_pct": float(round(v["cash_sgd"] / nav * 100, 2)) if nav else 0, "positions": rows,
    }  # fmt: skip
    return ok(summary)


@router.get("/funds/{fund_code}/exposure")
def exposure(
    fund_code: str,
    conn: DB,
    by: Annotated[str, Query(pattern="^(sector|issuer|type)$")] = "sector",
    as_of: Annotated[str | None, Query(description="DD/MM/YYYY")] = None,
) -> dict[str, Any]:
    if _fund(conn, fund_code) is None:
        return fail("ERR_FUND_NOT_FOUND", f"No fund {fund_code}")
    try:
        d = _as_of(as_of)
    except ValueError:
        return fail("ERR_INVALID_DATE", "Dates must be DD/MM/YYYY")
    assert d is not None
    v = valuation(conn, fund_code, d)
    nav: Decimal = v["nav_sgd"]
    buckets: dict[str, Decimal] = {"CASH": v["cash_sgd"]}
    for p in v["positions"]:
        key = {"sector": p.sector, "issuer": p.sec_name, "type": p.sec_type}[by]
        buckets[key] = buckets.get(key, Decimal(0)) + p.mv_sgd
    data = [
        {"bucket": k, "mv_sgd": float(mv), "weight_pct": float(round(mv / nav * 100, 2))}
        for k, mv in sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return ok({"fund_code": fund_code, "as_of": d.strftime("%d/%m/%Y"), "by": by,
               "nav_sgd": float(nav), "exposure": data})  # fmt: skip


@router.get("/funds/{fund_code}/mandate")
def mandate(fund_code: str, conn: DB) -> dict[str, Any]:
    if _fund(conn, fund_code) is None:
        return fail("ERR_FUND_NOT_FOUND", f"No fund {fund_code}")
    rows = conn.execute(
        "SELECT rule_id, rule_type, rule_param, limit_value, description FROM mandate_rules "
        "WHERE fund_code = %s ORDER BY rule_id",
        (fund_code,),
    ).fetchall()
    return ok(
        {"fund_code": fund_code, "enforced_by_pms": "N", "rules": [legacy_row(r) for r in rows]}
    )


@router.get("/funds/{fund_code}/transactions")
def transactions(
    fund_code: str,
    conn: DB,
    dt_from: Annotated[str | None, Query(description="DD/MM/YYYY")] = None,
    dt_to: Annotated[str | None, Query(description="DD/MM/YYYY")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1)] = 20,
) -> dict[str, Any]:
    """Served by the old settlement module: different field names (legacy quirk)."""
    per_page = min(per_page, settings.max_page_size)
    try:
        lo = parse_date(dt_from) if dt_from else None
        hi = parse_date(dt_to) if dt_to else None
    except ValueError:
        return fail("ERR_INVALID_DATE", "Dates must be DD/MM/YYYY")
    params = {"f": fund_code, "lo": lo, "hi": hi}
    where = ("fund_code = %(f)s AND (%(lo)s::date IS NULL OR trade_date >= %(lo)s) "
             "AND (%(hi)s::date IS NULL OR trade_date <= %(hi)s)")  # fmt: skip
    total = conn.execute(f"SELECT count(*) AS n FROM transactions WHERE {where}", params).fetchone()
    rows = conn.execute(
        f"""SELECT txn_id AS "TxnRef", trade_date AS "TradeDt", settle_date AS "SettleDt",
                   security_id AS "SecId", txn_type AS "TxnType", quantity AS "Qty",
                   price AS "Px", fx_rate AS "FxRate", fees_sgd AS "FeesSGD",
                   amount_sgd AS "AmtSGD", order_id AS "OrdRef"
            FROM transactions WHERE {where}
            ORDER BY trade_date DESC, txn_id DESC LIMIT %(lim)s OFFSET %(off)s""",
        {**params, "lim": per_page, "off": (page - 1) * per_page},
    ).fetchall()
    paging = {"page": page, "per_page": per_page, "total": total["n"] if total else 0}
    return ok([legacy_row(r) for r in rows], paging)
