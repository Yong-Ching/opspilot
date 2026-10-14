def main() -> None:
    import uvicorn

    from acme_oms.config import settings

    uvicorn.run("acme_oms.main:app", host="0.0.0.0", port=settings.port, reload=settings.debug)
