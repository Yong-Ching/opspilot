# Acme Market OMS (legacy)

A **simulated existing system**: Acme Market's order management system, built before OpsPilot existed.
OpsPilot must integrate with it **without changing it**, like an FDE would at a real customer.

Data: [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(CC BY-NC-SA 4.0), ~99k orders. Timestamps are shifted so the data ends on 2026-10-10.

## Run
```bash
make oms-data      # download Olist (~45 MB) into data/raw/olist
make oms-load      # load into the acme_oms database (~15 s)
make oms           # API on :8100 → docs at http://localhost:8100/docs
```

## API (send header `X-Acme-Key: dev-acme-key`)
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/orders/{order_id}` | Order + items, payments, reviews, refunds |
| GET | `/api/v1/orders?customer_id&status&dt_from&dt_to&page&per_page` | Dates as `DD/MM/YYYY` |
| GET | `/api/v1/customers/{customer_unique_id}/orders` | Order history of one person |
| POST | `/api/v1/refunds` | `{order_id, amount, reason, requested_by}` → `PENDING_REVIEW` |
| GET | `/api/v1/refunds/{refund_id}` | |
| PATCH | `/api/v1/orders/{order_id}/status` | `{status}` |

## Known quirks (deliberate, so integrating with it is realistic)
- **Business errors return HTTP 200** with `{"success": false, "error_code": "..."}`; auth errors return 401 `{"detail": ...}`. Two different error shapes.
- **Dates** are strings in `DD/MM/YYYY HH:MM:SS`, in both requests and responses.
- **`customer_id` is per order**, not per person. Use `customer_unique_id` for a person's history.
- **`per_page` is silently capped** at 50. Check `paging.per_page` in the response.
- Column names come from the source system as-is: Portuguese category names, the `product_name_lenght` typo.
- Error messages are in Portuguese.

## Events (transactional outbox)
Refund requests and status changes are recorded in the `outbox` table in the same transaction,
then delivered to `ACME_WEBHOOK_URLS` by the dispatcher (`uv run python -m acme_oms.outbox`).
