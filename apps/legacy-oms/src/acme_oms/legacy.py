"""Quirks of Acme's legacy API, kept on purpose so integrating with it is realistic.

- Dates are strings in Brazilian format: "DD/MM/YYYY HH:MM:SS".
- Responses are wrapped in an envelope: {"success": ..., "data": ..., "paging": ...}.
- Business errors return HTTP 200 with success=false and an error_code (!).
- Auth errors, by contrast, are plain HTTP 401 with FastAPI's {"detail": ...} body.
- Page size is silently capped at ACME_MAX_PAGE_SIZE.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

DATE_FMT = "%d/%m/%Y %H:%M:%S"
DATE_ONLY_FMT = "%d/%m/%Y"


def fmt_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime(DATE_FMT)
    if isinstance(value, Decimal):
        return float(value)
    return value


def legacy_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: fmt_value(v) for k, v in row.items()}


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, DATE_ONLY_FMT)


def ok(data: Any, paging: dict[str, int] | None = None) -> dict[str, Any]:
    return {"success": True, "data": data, "paging": paging}


def fail(error_code: str, error_message: str) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error_code": error_code,
        "error_message": error_message,
    }
