def main() -> None:
    import uvicorn

    from hc_pms.config import settings

    uvicorn.run("hc_pms.main:app", host="0.0.0.0", port=settings.port, reload=settings.debug)
