from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="OPSPILOT_", extra="ignore"
    )

    env: str = "dev"
    debug: bool = False
    port: int = 8000
    database_url: str = "postgresql://opspilot:opspilot@localhost:5432/opspilot"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
