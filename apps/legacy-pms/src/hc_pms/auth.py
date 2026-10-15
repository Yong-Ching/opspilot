from typing import Annotated

from fastapi import Header, HTTPException

from hc_pms.config import settings


def require_api_key(x_hc_apikey: Annotated[str | None, Header()] = None) -> str:
    # One shared service key: the PMS trusts the CALLER to say which user is acting
    # (e.g. `proposed_by` in the body). ResearchPilot must authenticate users itself.
    if x_hc_apikey is None or x_hc_apikey not in settings.api_keys:
        raise HTTPException(status_code=401, detail="AUTH_INVALID_KEY")
    return x_hc_apikey
