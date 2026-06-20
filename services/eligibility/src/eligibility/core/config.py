from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://claimvoice:changeme@localhost:5432/claimvoice"
    redis_url: str = "redis://localhost:6379"

    # Anthropic — only required when fact_check_mode == "claude".
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    # Fact-check grounding: "mock" = deterministic structured matcher (no key);
    # "claude" = LLM entailment over (answer, facts).
    fact_check_mode: Literal["mock", "claude"] = "mock"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
