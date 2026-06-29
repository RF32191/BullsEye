from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/bullseye"
    fmp_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Token economics — gpt-4o-mini keeps AI costs low (~$0.01/prediction)
    tokens_per_prediction: int = 250
    tokens_per_technical_prediction: int = 0
    tokens_per_chat_message: int = 75
    initial_token_grant: int = 1000
    free_daily_token_grant: int = 500

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "*"

    # When true, skip paid AI/chat APIs and return deterministic mock predictions.
    # Congressional, insider, and Polymarket whale feeds always attempt live sources first.
    mock_mode: bool = False

    # Optional — higher rate limits for congressional trade disclosures
    capitol_exposed_api_key: str = ""
    admin_cron_key: str = "dev-cron-key"

    # Allow client-side dev purchases without App Store receipt (disable in production when StoreKit validation is live)
    allow_dev_purchases: bool = True


settings = Settings()
