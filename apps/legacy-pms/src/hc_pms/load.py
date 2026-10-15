"""Build the Harbourfront PMS database: reference data, market data, then the synthetic firm.

    uv run hc-pms-load --universe ../../data/universe.csv --market-dir ../../data/raw/market --reset

Market data comes from `data/scripts/fetch_market_data.py` (run that first).
"""

import argparse
import csv
from importlib.resources import files
from pathlib import Path
from typing import LiteralString, cast

import psycopg
from psycopg import sql

from hc_pms.config import settings
from hc_pms.seed import seed

TABLES = [
    "outbox", "orders", "restricted_list", "transactions", "cash_flows", "mandate_rules",
    "funds", "clients", "fx_rates", "dividends", "prices", "security_identifiers",
    "securities", "users",
]  # fmt: skip

# Identifiers that no longer resolve but still appear in old documents and trade records.
RETIRED_SGX_CODES = {"9A4U": ["J91U"]}


def _sql_file(name: str) -> sql.SQL:
    # Trusted: these files ship inside the package; they never contain user input.
    return sql.SQL(cast(LiteralString, files("hc_pms").joinpath(name).read_text()))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_reference(conn: psycopg.Connection, universe: list[dict[str, str]]) -> dict[str, str]:
    """Insert securities + identifiers. Returns yahoo_ticker -> security_id."""
    by_yahoo: dict[str, str] = {}
    for i, row in enumerate(universe, start=1):
        sid = f"HC{i * 7 + 100:06d}"  # internal IDs: deliberately unrelated to tickers
        by_yahoo[row["yahoo_ticker"]] = sid
        conn.execute(
            "INSERT INTO securities VALUES (%s, %s, %s, %s, %s, 100, %s)",
            (sid, row["name"], "REIT" if row["type"] == "REIT" else "EQUITY", row["sector"],
             row["currency"], row["sponsor"] or None),
        )  # fmt: skip
        conn.execute(
            "INSERT INTO security_identifiers VALUES "
            "(%s, 'SGX', %s, TRUE), (%s, 'YAHOO', %s, TRUE)",
            (sid, row["sgx_code"], sid, row["yahoo_ticker"]),
        )
        for old in RETIRED_SGX_CODES.get(row["sgx_code"], []):
            conn.execute(
                "INSERT INTO security_identifiers VALUES (%s, 'SGX', %s, FALSE)", (sid, old)
            )
    return by_yahoo


def load_market(conn: psycopg.Connection, market_dir: Path, by_yahoo: dict[str, str]) -> int:
    n = 0
    with conn.cursor() as cur:
        with cur.copy("COPY prices FROM STDIN") as copy:
            for r in _read_csv(market_dir / "prices.csv"):
                if r["yahoo_ticker"] in by_yahoo:
                    copy.write_row((by_yahoo[r["yahoo_ticker"]], r["date"],
                                    round(float(r["close"]) * 100)))  # fmt: skip
                    n += 1
        with cur.copy("COPY dividends FROM STDIN") as copy:
            for r in _read_csv(market_dir / "dividends.csv"):
                if r["yahoo_ticker"] in by_yahoo:
                    copy.write_row((by_yahoo[r["yahoo_ticker"]], r["ex_date"], r["amount"]))
        with cur.copy("COPY fx_rates FROM STDIN") as copy:
            for r in _read_csv(market_dir / "fx.csv"):
                copy.write_row((r["ccy"], r["date"], r["rate_to_sgd"]))
    return n


def load(
    database_url: str, universe_path: Path, market_dir: Path, *, reset: bool, seed_value: int = 42
) -> dict[str, int]:
    with psycopg.connect(database_url) as conn:
        if reset:
            for table in TABLES:
                conn.execute(
                    sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table))
                )
        conn.execute(_sql_file("schema.sql"))
        by_yahoo = load_reference(conn, _read_csv(universe_path))
        n_prices = load_market(conn, market_dir, by_yahoo)
        counts = {"securities": len(by_yahoo), "prices": n_prices, **seed(conn, seed_value)}
        conn.execute(_sql_file("indexes.sql"))
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("ANALYZE")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--market-dir", type=Path, required=True)
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    counts = load(args.database_url, args.universe, args.market_dir, reset=args.reset,
                  seed_value=args.seed)  # fmt: skip
    for k, v in counts.items():
        print(f"  {k:<14} {v:>8,}")


if __name__ == "__main__":
    main()
