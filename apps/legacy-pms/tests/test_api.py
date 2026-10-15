from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from tests.conftest import KEY

API = "/api/v1"


def sid(client: TestClient, code: str) -> str:
    return client.get(f"{API}/securities/lookup", params={"code": code}, headers=KEY).json()[
        "data"
    ]["security_id"]


def propose(client: TestClient, **overrides: Any) -> dict[str, Any]:
    body = {
        "fund_code": "HCREIT", "security_id": sid(client, "M44U"), "side": "BUY",
        "quantity": 1000, "rationale": "Logistics rents recovering", "proposed_by": "u_raj_k",
    } | overrides  # fmt: skip
    return client.post(f"{API}/orders", json=body, headers=KEY).json()


def decide(client: TestClient, order_id: int, action: str, user: str, note: str | None = None):  # type: ignore[no-untyped-def]
    return client.post(
        f"{API}/orders/{order_id}/{action}", json={"user_id": user, "note": note}, headers=KEY
    ).json()


# ── reference data & quirks ──────────────────────────────────────────────────────────────────
def test_health_and_auth(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    r = client.get(f"{API}/funds")
    assert r.status_code == 401 and r.json() == {"detail": "AUTH_INVALID_KEY"}


def test_retired_code_resolves_to_current_security(client: TestClient) -> None:
    data = client.get(f"{API}/securities/lookup", params={"code": "J91U"}, headers=KEY).json()[
        "data"
    ]
    assert data["sgx_code"] == "9A4U"
    assert data["matched_code_current"] == "N"


def test_unknown_code_is_http_200_error(client: TestClient) -> None:
    r = client.get(f"{API}/securities/lookup", params={"code": "NOPE"}, headers=KEY)
    assert r.status_code == 200 and r.json()["error_code"] == "ERR_SECURITY_NOT_FOUND"


def test_holdings_weights_and_cash_add_up(client: TestClient) -> None:
    data = client.get(f"{API}/funds/HCREIT/holdings", headers=KEY).json()["data"]
    total = sum(p["weight_pct"] for p in data["positions"]) + data["cash_pct"]
    assert total == pytest.approx(100, abs=0.1)
    first = data["positions"][0]
    assert isinstance(first["quantity"], int) and isinstance(first["px_minor"], int)  # cents


def test_usd_security_valued_in_sgd(client: TestClient) -> None:
    data = client.get(f"{API}/funds/HCREIT/holdings", headers=KEY).json()["data"]
    usd = [p for p in data["positions"] if p["ccy"] == "USD"]
    assert usd, "fixture fund should hold the USD REIT"
    p = usd[0]
    assert p["mv_sgd"] == pytest.approx(
        p["quantity"] * p["px_minor"] / 100 * p["fx_rate"], rel=1e-6
    )


def test_exposure_sums_to_100(client: TestClient) -> None:
    data = client.get(f"{API}/funds/HCDIV/exposure", params={"by": "sector"}, headers=KEY).json()
    assert sum(e["weight_pct"] for e in data["data"]["exposure"]) == pytest.approx(100, abs=0.1)


def test_mandate_rules_not_enforced_by_pms(client: TestClient) -> None:
    data = client.get(f"{API}/funds/HCDIV/mandate", headers=KEY).json()["data"]
    assert data["enforced_by_pms"] == "N"
    assert {r["rule_type"] for r in data["rules"]} >= {"MAX_ISSUER_PCT", "MAX_SECTOR_PCT"}


def test_transactions_use_old_field_names_and_capped_paging(client: TestClient) -> None:
    body = client.get(
        f"{API}/funds/HCREIT/transactions", params={"per_page": 500}, headers=KEY
    ).json()
    assert body["paging"]["per_page"] == 50
    assert {"TxnRef", "TradeDt", "SecId", "AmtSGD"} <= set(body["data"][0])


def test_iso_date_rejected(client: TestClient) -> None:
    body = client.get(f"{API}/funds/HCREIT/holdings", params={"as_of": "2026-01-31"}, headers=KEY)
    assert body.json()["error_code"] == "ERR_INVALID_DATE"


def test_client_record_exposes_full_nric(client: TestClient) -> None:
    data = client.get(f"{API}/clients/C00001", headers=KEY).json()["data"]
    assert len(data["nric"]) == 9 and data["nric"][0] in "ST"  # legacy PII exposure


def test_restricted_check_does_not_leak_reason(client: TestClient) -> None:
    data = client.get(
        f"{API}/restricted-list/check", params={"security_id": sid(client, "AJBU")}, headers=KEY
    ).json()["data"]
    assert data["restricted"] == "Y" and "reason" not in data


# ── order workflow ───────────────────────────────────────────────────────────────────────────
def test_cannot_propose_restricted(client: TestClient) -> None:
    assert propose(client, security_id=sid(client, "AJBU"))["error_code"] == "ERR_RESTRICTED"


def test_board_lot_enforced(client: TestClient) -> None:
    assert propose(client, quantity=150)["error_code"] == "ERR_BOARD_LOT"


def test_rm_cannot_propose(client: TestClient) -> None:
    assert propose(client, proposed_by="u_ng_d")["error_code"] == "ERR_NOT_AUTHORISED"


def test_cannot_sell_more_than_held(client: TestClient) -> None:
    body = propose(client, side="SELL", quantity=1_000_000_000)
    assert body["error_code"] == "ERR_INSUFFICIENT_HOLDING"


def test_only_the_funds_pm_can_approve(client: TestClient) -> None:
    order_id = propose(client)["data"]["order_id"]
    assert decide(client, order_id, "approve", "u_lim_jh")["error_code"] == "ERR_NOT_AUTHORISED"
    assert decide(client, order_id, "approve", "u_ong_bk")["error_code"] == "ERR_NOT_AUTHORISED"


def test_four_eyes(client: TestClient) -> None:
    order_id = propose(client, proposed_by="u_tan_wl")["data"]["order_id"]
    assert decide(client, order_id, "approve", "u_tan_wl")["error_code"] == "ERR_FOUR_EYES"


def test_restriction_added_after_proposal_blocks_approval(client: TestClient) -> None:
    c38u = sid(client, "C38U")
    order_id = propose(client, security_id=c38u)["data"]["order_id"]
    added = client.post(
        f"{API}/restricted-list",
        json={"security_id": c38u, "reason": "Test restriction", "user_id": "u_goh_sp"},
        headers=KEY,
    ).json()
    assert added["success"]
    assert decide(client, order_id, "approve", "u_tan_wl")["error_code"] == "ERR_RESTRICTED"
    removed = client.post(
        f"{API}/restricted-list/{added['data']['entry_id']}/remove",
        json={"user_id": "u_goh_sp"},
        headers=KEY,
    ).json()
    assert removed["success"]


def test_only_compliance_changes_restricted_list(client: TestClient) -> None:
    body = client.post(
        f"{API}/restricted-list",
        json={"security_id": sid(client, "D05"), "reason": "Trying", "user_id": "u_tan_wl"},
        headers=KEY,
    ).json()
    assert body["error_code"] == "ERR_NOT_AUTHORISED"


def test_reject_needs_a_note_and_compliance_can_reject(client: TestClient) -> None:
    order_id = propose(client)["data"]["order_id"]
    assert decide(client, order_id, "reject", "u_goh_sp")["error_code"] == "ERR_NOTE_REQUIRED"
    assert (
        decide(client, order_id, "reject", "u_goh_sp", "Concentration")["data"]["status"]
        == "REJECTED"
    )


def test_approve_and_execute_updates_holdings_and_cash(client: TestClient) -> None:
    m44u = sid(client, "M44U")

    def position_and_cash() -> tuple[int, float]:
        data = client.get(f"{API}/funds/HCREIT/holdings", headers=KEY).json()["data"]
        qty = next((p["quantity"] for p in data["positions"] if p["security_id"] == m44u), 0)
        return qty, data["cash_sgd"]

    qty_before, cash_before = position_and_cash()
    order_id = propose(client, quantity=1000)["data"]["order_id"]
    assert decide(client, order_id, "approve", "u_tan_wl", "ok")["data"]["status"] == "APPROVED"
    executed = client.post(f"{API}/orders/{order_id}/execute", headers=KEY).json()
    assert executed["data"]["status"] == "EXECUTED"
    qty_after, cash_after = position_and_cash()
    assert qty_after == qty_before + 1000
    assert cash_after == pytest.approx(cash_before + executed["data"]["amount_sgd"], abs=0.01)
    again = client.post(f"{API}/orders/{order_id}/execute", headers=KEY).json()
    assert again["error_code"] == "ERR_INVALID_STATE"  # never fill twice


# ── Phase 1 outbox (yours) ───────────────────────────────────────────────────────────────────
# These fail until you implement hc_pms/outbox.py. `strict=True` means that once your code makes
# them pass, pytest reports XPASS as a failure, reminding you to delete the xfail marker.


@pytest.mark.xfail(reason="Phase 1: implement outbox.record_event", strict=True)
def test_proposal_writes_outbox_event_in_same_transaction(
    client: TestClient, db: psycopg.Connection
) -> None:
    order_id = str(propose(client)["data"]["order_id"])
    row = db.execute(
        "SELECT event_type, published_at FROM outbox WHERE aggregate_id = %s", (order_id,)
    ).fetchone()
    assert row == ("order.proposed", None)


@pytest.mark.xfail(reason="Phase 1: implement outbox.record_event", strict=True)
def test_failed_business_change_writes_no_event(client: TestClient, db: psycopg.Connection) -> None:
    before = db.execute("SELECT count(*) FROM outbox").fetchone()
    assert propose(client, quantity=150)["error_code"] == "ERR_BOARD_LOT"  # rejected
    assert db.execute("SELECT count(*) FROM outbox").fetchone() == before
    order_id = propose(client)["data"]["order_id"]  # accepted
    decide(client, order_id, "approve", "u_tan_wl", "ok")
    after = db.execute("SELECT count(*) FROM outbox").fetchone()
    assert after is not None and before is not None and after[0] == before[0] + 2
