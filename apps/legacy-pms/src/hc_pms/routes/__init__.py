from typing import Annotated

from fastapi import APIRouter, Depends

from hc_pms.auth import require_api_key
from hc_pms.db import Conn, get_conn

DB = Annotated[Conn, Depends(get_conn)]


def make_router() -> APIRouter:
    from hc_pms.routes import clients, funds, orders, reference, restricted

    router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])
    for module in (reference, funds, clients, orders, restricted):
        router.include_router(module.router)
    return router
