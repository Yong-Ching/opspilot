from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from hc_pms.config import settings
from hc_pms.db import close_pool, open_pool
from hc_pms.routes import make_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    open_pool(settings.database_url)
    yield
    close_pool()


app = FastAPI(
    title="Harbourfront Capital PMS",
    version="4.7.2-legacy",
    description="Harbourfront Capital's existing Portfolio Management System. "
    "Auth: send the `X-HC-ApiKey` header. Dates are DD/MM/YYYY; prices are in cents.",
    lifespan=lifespan,
)
app.include_router(make_router())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "hc-pms"}
