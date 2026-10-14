import re
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from tests.conftest import KEY

LEGACY_DATE = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$")


def first_order(client: TestClient, status: str) -> dict[str, Any]:
    body = client.get("/api/v1/orders", params={"status": status}, headers=KEY).json()
    assert body["success"] and body["data"], f"no fixture order with status={status}"
    return body["data"][0]


def test_health(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"


def test_missing_api_key_is_401(client: TestClient) -> None:
    r = client.get("/api/v1/orders")
    assert r.status_code == 401
    assert r.json() == {"detail": "AUTH_INVALID_KEY"}


def test_order_detail_uses_legacy_format(client: TestClient) -> None:
    order_id = first_order(client, "delivered")["order_id"]
    body = client.get(f"/api/v1/orders/{order_id}", headers=KEY).json()
    assert body["success"] is True
    data = body["data"]
    assert LEGACY_DATE.match(data["order_purchase_timestamp"])
    assert data["items"] and data["payments"]
    assert "customer_unique_id" in data


def test_not_found_is_http_200_with_error_code(client: TestClient) -> None:
    r = client.get("/api/v1/orders/does-not-exist", headers=KEY)
    assert r.status_code == 200
    assert r.json()["success"] is False
    assert r.json()["error_code"] == "ORDER_NOT_FOUND"


def test_page_size_is_silently_capped(client: TestClient) -> None:
    body = client.get("/api/v1/orders", params={"per_page": 500}, headers=KEY).json()
    assert body["paging"]["per_page"] == 50
    assert body["paging"]["total"] == 8


def test_iso_date_is_rejected(client: TestClient) -> None:
    body = client.get("/api/v1/orders", params={"dt_from": "2026-09-01"}, headers=KEY).json()
    assert body["error_code"] == "INVALID_DATE"


def test_legacy_date_filter(client: TestClient) -> None:
    body = client.get("/api/v1/orders", params={"dt_from": "01/01/2030"}, headers=KEY).json()
    assert body["success"] and body["data"] == []


def test_customer_history(client: TestClient) -> None:
    order_id = first_order(client, "delivered")["order_id"]
    cuid = client.get(f"/api/v1/orders/{order_id}", headers=KEY).json()["data"][
        "customer_unique_id"
    ]
    body = client.get(f"/api/v1/customers/{cuid}/orders", headers=KEY).json()
    assert body["success"] and order_id in [o["order_id"] for o in body["data"]]


def refund(client: TestClient, order_id: str, amount: float) -> dict[str, Any]:
    payload = {
        "order_id": order_id,
        "amount": amount,
        "reason": "item damaged",
        "requested_by": "t",
    }
    return client.post("/api/v1/refunds", json=payload, headers=KEY).json()


def test_refund_not_allowed_for_processing_order(client: TestClient) -> None:
    order_id = first_order(client, "processing")["order_id"]
    assert refund(client, order_id, 1.00)["error_code"] == "REFUND_NOT_ALLOWED"


def test_refund_cannot_exceed_amount_paid(client: TestClient) -> None:
    order_id = first_order(client, "shipped")["order_id"]
    assert refund(client, order_id, 1_000_000)["error_code"] == "REFUND_EXCEEDS_PAID"


def test_refund_created_pending_review(client: TestClient) -> None:
    order_id = first_order(client, "delivered")["order_id"]
    body = refund(client, order_id, 5.00)
    assert body["success"] and body["data"]["status"] == "PENDING_REVIEW"
    got = client.get(f"/api/v1/refunds/{body['data']['refund_id']}", headers=KEY).json()
    assert got["data"]["amount"] == 5.0


def test_invalid_status_rejected(client: TestClient) -> None:
    order_id = first_order(client, "shipped")["order_id"]
    r = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "lost"}, headers=KEY)
    assert r.json()["error_code"] == "INVALID_STATUS"


# ── Phase 1, step 3 ────────────────────────────────────────────────────────────────────────
# These fail until you implement acme_oms/outbox.py. `strict=True` means that once your code
# makes them pass, pytest reports XPASS as a failure, reminding you to delete the xfail marker.


@pytest.mark.xfail(reason="Phase 1 step 3: implement outbox.record_event", strict=True)
def test_refund_writes_outbox_event_in_same_transaction(
    client: TestClient, db: psycopg.Connection
) -> None:
    order_id = first_order(client, "delivered")["order_id"]
    refund_id = str(refund(client, order_id, 1.00)["data"]["refund_id"])
    row = db.execute(
        "SELECT event_type, published_at FROM outbox WHERE aggregate_id = %s", (refund_id,)
    ).fetchone()
    assert row == ("refund.requested", None)


@pytest.mark.xfail(reason="Phase 1 step 3: implement outbox.record_event", strict=True)
def test_failed_business_change_writes_no_event(client: TestClient, db: psycopg.Connection) -> None:
    before = db.execute("SELECT count(*) FROM outbox").fetchone()
    order_id = first_order(client, "processing")["order_id"]
    refund(client, order_id, 1.00)  # rejected: REFUND_NOT_ALLOWED
    after = db.execute("SELECT count(*) FROM outbox").fetchone()
    assert before == after
    # ...and status updates DO write one:
    r = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "invoiced"}, headers=KEY)
    assert r.json()["success"]
    assert db.execute("SELECT count(*) FROM outbox").fetchone()[0] == before[0] + 1  # type: ignore[index]
