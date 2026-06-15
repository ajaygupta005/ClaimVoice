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

    # TTS provider: "browser" means no server-side TTS; "google" uses Google Cloud TTS.
    voice_agent_tts_provider: Literal["browser", "google"] = "browser"
    google_tts_voice_name: str = "en-US-Chirp3-HD-Aoede"
    google_tts_language_code: str = "en-US"
    # Google Application Credentials path (optional — falls back to ADC)
    google_application_credentials: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
