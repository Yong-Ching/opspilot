"""Load the Olist CSVs into the Acme OMS database.

    uv run acme-oms-load --data-dir ../../data/raw/olist --reset

The source data tails off with a trickle of stray (mostly canceled) orders, so we:
  1. find the last "real" day: the last day with at least MIN_DAILY_ORDERS orders,
  2. trim the stray orders after it,
  3. shift all timestamps by whole days so that day lands on --shift-to.
This makes the 2016-2018 dataset look like a live system ("late deliveries last month" works).
"""

import argparse
import csv
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import LiteralString, cast

import psycopg
from psycopg import sql

from acme_oms.config import settings

# (table, csv file) in foreign-key order. Geolocation (1M rows) is not needed and is skipped.
TABLES = [
    ("product_category_name_translation", "product_category_name_translation.csv"),
    ("customers", "olist_customers_dataset.csv"),
    ("sellers", "olist_sellers_dataset.csv"),
    ("products", "olist_products_dataset.csv"),
    ("orders", "olist_orders_dataset.csv"),
    ("order_items", "olist_order_items_dataset.csv"),
    ("order_payments", "olist_order_payments_dataset.csv"),
    ("order_reviews", "olist_order_reviews_dataset.csv"),
]

TIMESTAMP_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}

MIN_DAILY_ORDERS = 10

DROP_ORDER = [
    "outbox",
    "refund_requests",
    *[t for t, _ in reversed(TABLES)],
]


def _sql_file(name: str) -> sql.SQL:
    # Trusted: these files ship inside the package; they never contain user input.
    return sql.SQL(cast(LiteralString, files("acme_oms").joinpath(name).read_text()))


def _copy_csv(conn: psycopg.Connection, table: str, path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as f:
        columns = next(csv.reader(f))
    stmt = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns))
    )
    with path.open("rb") as f, conn.cursor() as cur:
        with cur.copy(stmt) as copy:
            while chunk := f.read(1 << 20):
                copy.write(chunk)
        return cur.rowcount


def _trim_and_shift(conn: psycopg.Connection, shift_to: date) -> tuple[int, int]:
    """Returns (orders trimmed, days shifted)."""
    row = conn.execute(
        """SELECT max(d) FROM (
             SELECT order_purchase_timestamp::date AS d FROM orders
             GROUP BY 1 HAVING count(*) >= %s) t""",
        (MIN_DAILY_ORDERS,),
    ).fetchone()
    if row is None or row[0] is None:
        return 0, 0
    last_real_day: date = row[0]
    stray = "SELECT order_id FROM orders WHERE order_purchase_timestamp >= %(cut)s::date + 1"
    for table in ("order_items", "order_payments", "order_reviews"):
        conn.execute(
            sql.SQL("DELETE FROM {} WHERE order_id IN ({})").format(
                sql.Identifier(table), sql.SQL(stray)
            ),
            {"cut": last_real_day},
        )
    deleted = conn.execute(
        "DELETE FROM orders WHERE order_purchase_timestamp >= %(cut)s::date + 1 "
        "RETURNING customer_id",
        {"cut": last_real_day},
    ).fetchall()
    conn.execute("DELETE FROM customers WHERE customer_id = ANY(%s)", ([r[0] for r in deleted],))
    days = (shift_to - last_real_day).days
    for table, columns in TIMESTAMP_COLUMNS.items():
        sets = sql.SQL(", ").join(
            sql.SQL("{c} = {c} + make_interval(days => %(d)s)").format(c=sql.Identifier(c))
            for c in columns
        )
        conn.execute(sql.SQL("UPDATE {} SET {}").format(sql.Identifier(table), sets), {"d": days})
    return len(deleted), days


def load(database_url: str, data_dir: Path, *, reset: bool, shift_to: date) -> None:
    with psycopg.connect(database_url) as conn:
        if reset:
            for table in DROP_ORDER:
                conn.execute(
                    sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table))
                )
        conn.execute(_sql_file("schema.sql"))
        for table, filename in TABLES:
            n = _copy_csv(conn, table, data_dir / filename)
            print(f"  {table:<36} {n:>8,} rows")
        trimmed, days = _trim_and_shift(conn, shift_to)
        print(f"  trimmed {trimmed} stray trailing orders")
        print(f"  shifted timestamps by {days:,} days (last real day -> {shift_to})")
        conn.execute(_sql_file("indexes.sql"))
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("ANALYZE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables")
    parser.add_argument("--shift-to", type=date.fromisoformat, default=date(2026, 10, 10))
    args = parser.parse_args()
    load(args.database_url, args.data_dir, reset=args.reset, shift_to=args.shift_to)


if __name__ == "__main__":
    main()
