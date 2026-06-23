from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://claimvoice:changeme@localhost:5433/claimvoice"
    redis_url: str = "redis://localhost:6379"
    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
