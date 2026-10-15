"""Quirks of Harbourfront's legacy PMS API, kept on purpose so integrating with it is realistic.

- Dates are strings in Singapore format: "DD/MM/YYYY" (timestamps "DD/MM/YYYY HH:MM:SS").
- Responses are wrapped in an envelope: {"success": ..., "data": ..., "paging": ...}.
- Business errors return HTTP 200 with success=false and an error_code (!).
- Auth errors, by contrast, are plain HTTP 401 with FastAPI's {"detail": ...} body.
- Page size is silently capped at HC_MAX_PAGE_SIZE.
- Prices are in MINOR units (cents) of the security's currency; cash amounts are SGD dollars.
- Flags are "Y"/"N" strings, not booleans.
- The transactions endpoint comes from an older module and uses different field names.
- Client records include the full NRIC.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

DATE_FMT = "%d/%m/%Y"
TIMESTAMP_FMT = "%d/%m/%Y %H:%M:%S"


def fmt_value(value: Any) -> Any:
    if isinstance(value, datetime):  # check before date: datetime is a subclass of date
        return value.strftime(TIMESTAMP_FMT)
    if isinstance(value, date):
        return value.strftime(DATE_FMT)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bool):
        return "Y" if value else "N"
    return value


def legacy_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: fmt_value(v) for k, v in row.items()}


def parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FMT).date()


def ok(data: Any, paging: dict[str, int] | None = None) -> dict[str, Any]:
    return {"success": True, "data": data, "paging": paging}


def fail(error_code: str, error_message: str) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error_code": error_code,
        "error_message": error_message,
    }
