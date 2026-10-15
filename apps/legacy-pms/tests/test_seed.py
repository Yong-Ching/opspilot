"""Invariants of the synthetic firm: if these break, the demo data is not believable."""

import psycopg
import pytest

from hc_pms.seed import nric


def test_nric_checksum_known_example() -> None:
    assert nric("S", "1234567") == "S1234567D"


def test_cash_never_negative_at_end_of_day(db: psycopg.Connection) -> None:
    row = db.execute(
        """WITH ev AS (SELECT fund_code, flow_date d, amount_sgd a FROM cash_flows
                       UNION ALL SELECT fund_code, trade_date, amount_sgd FROM transactions),
           daily AS (SELECT fund_code, d, sum(a) a FROM ev GROUP BY 1, 2)
           SELECT min(bal) FROM (
             SELECT sum(a) OVER (PARTITION BY fund_code ORDER BY d) bal FROM daily) x"""
    ).fetchone()
    assert row is not None and row[0] >= 0


def test_trades_are_in_board_lots(db: psycopg.Connection) -> None:
    row = db.execute(
        "SELECT count(*) FROM transactions WHERE txn_type <> 'DIVIDEND' AND quantity % 100 <> 0"
    ).fetchone()
    assert row == (0,)


def test_excluded_security_never_bought(db: psycopg.Connection) -> None:
    row = db.execute(
        """SELECT count(*) FROM transactions t JOIN mandate_rules r
           ON r.fund_code = t.fund_code AND r.rule_type = 'EXCLUDE_SECURITY'
           AND r.rule_param = t.security_id WHERE t.txn_type = 'BUY'"""
    ).fetchone()
    assert row == (0,)


@pytest.mark.parametrize("fund_code", ["HCREIT", "HCDIV", "MND-001"])
def test_issuer_limits_respected_at_end(client, fund_code: str) -> None:  # type: ignore[no-untyped-def]
    from tests.conftest import KEY

    limits = client.get(f"/api/v1/funds/{fund_code}/mandate", headers=KEY).json()["data"]["rules"]
    cap = next(r["limit_value"] for r in limits if r["rule_type"] == "MAX_ISSUER_PCT")
    positions = client.get(f"/api/v1/funds/{fund_code}/holdings", headers=KEY).json()["data"]
    assert max(p["weight_pct"] for p in positions["positions"]) <= cap
