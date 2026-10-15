from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="HC_", extra="ignore")

    debug: bool = False
    port: int = 8100
    database_url: str = "postgresql://hc:hc@localhost:5432/hc_pms"
    api_keys: list[str] = ["dev-hc-key"]
    max_page_size: int = 50
    webhook_urls: list[str] = []


settings = Settings()
