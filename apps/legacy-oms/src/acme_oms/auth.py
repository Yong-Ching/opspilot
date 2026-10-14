from typing import Annotated

from fastapi import Header, HTTPException

from acme_oms.config import settings


def require_api_key(x_acme_key: Annotated[str | None, Header()] = None) -> str:
    if x_acme_key is None or x_acme_key not in settings.api_keys:
        raise HTTPException(status_code=401, detail="AUTH_INVALID_KEY")
    return x_acme_key
