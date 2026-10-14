from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ACME_", extra="ignore")

    debug: bool = False
    port: int = 8100
    database_url: str = "postgresql://acme:acme@localhost:5432/acme_oms"
    api_keys: list[str] = ["dev-acme-key"]
    max_page_size: int = 50
    webhook_urls: list[str] = []


settings = Settings()
