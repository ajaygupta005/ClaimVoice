from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://claimvoice:changeme@localhost:5432/claimvoice"
    redis_url: str = "redis://localhost:6379"

    # /providers/near defaults
    default_radius_km: float = 25.0
    near_max_limit: int = 50

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
