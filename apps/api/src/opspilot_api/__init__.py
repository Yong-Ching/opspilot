def main() -> None:
    import uvicorn

    from opspilot_api.config import settings

    uvicorn.run(
        "opspilot_api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )
