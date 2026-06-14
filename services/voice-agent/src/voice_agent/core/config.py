from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://claimvoice:changeme@localhost:5432/claimvoice"
    redis_url: str = "redis://localhost:6379"

    # Answer composer: "mock" runs deterministic logic; "claude" calls Anthropic.
    # Default is "mock" so local startup works without an API key.
    voice_agent_answer_mode: Literal["mock", "claude"] = "mock"

    # Anthropic — only required when voice_agent_answer_mode == "claude"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
