"""Transactional outbox. ── Phase 1, step 3: YOU implement this file. ──

Goal: every business change (refund created, order status changed) produces an event that is
delivered to webhook subscribers *at least once*, even if the server crashes right after the change.

Part A: record_event()
    Insert a row into the `outbox` table (see schema.sql) using the SAME `conn` the endpoint used
    for the business change, so both commit or roll back together. Do NOT commit here.

Part B: dispatcher (a separate process: `uv run python -m acme_oms.outbox`)
    Loop: fetch unpublished events in order, POST each one as JSON to every URL in
    settings.webhook_urls, then mark it published. On failure: increment `attempts`, store
    `last_error`, and retry later (think about backoff and a max-attempts cut-off).

Questions to answer in your code or a comment (likely interview questions):
    1. Why not just call the webhook directly inside the endpoint?
    2. Two dispatcher processes run at once. How do you stop them sending the same event twice?
       (hint: SELECT ... FOR UPDATE SKIP LOCKED)
    3. Delivery is "at least once". What must the *receiver* do about duplicates?
"""

from typing import Any

from acme_oms.db import Conn


def record_event(conn: Conn, event_type: str, aggregate_id: str, payload: dict[str, Any]) -> None:
    # TODO(you): Part A. Currently a no-op so the API works before you implement it.
    _ = (conn, event_type, aggregate_id, payload)


def run_dispatcher() -> None:
    # TODO(you): Part B.
    raise NotImplementedError


if __name__ == "__main__":
    run_dispatcher()
