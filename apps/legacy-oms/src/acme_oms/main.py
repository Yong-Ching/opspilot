from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from acme_oms.config import settings
from acme_oms.db import close_pool, open_pool
from acme_oms.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    open_pool(settings.database_url)
    yield
    close_pool()


app = FastAPI(
    title="Acme Market OMS",
    version="3.2.1-legacy",
    description="Acme Market's existing Order Management System. "
    "Auth: send `X-Acme-Key` header. Dates are DD/MM/YYYY.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "acme-oms"}
