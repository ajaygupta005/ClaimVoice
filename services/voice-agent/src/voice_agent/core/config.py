from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://claimvoice:changeme@localhost:5432/claimvoice"
    redis_url: str = "redis://localhost:6379"

    # Backend service URLs for real tool calls (tool_mode == "http")
    eligibility_base_url: str = "http://localhost:8002"
    providers_base_url: str = "http://localhost:8003"
    # Tools: "mock" = deterministic inline logic; "http" = call WS-4/WS-5 services
    # (falls back to the mock string on any HTTP error so dev/tests stay green).
    tool_mode: Literal["mock", "http"] = "mock"

    # Answer composer: "mock" runs deterministic logic; "claude" calls Anthropic.
    # Default is "mock" so local startup works without an API key.
    voice_agent_answer_mode: Literal["mock", "claude"] = "mock"

    # Anthropic — only required when voice_agent_answer_mode == "claude"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # TTS provider: "browser" falls back to local system TTS when available;
    # "system" forces local OS TTS; "google" uses Google Cloud TTS first;
    # "cartesia" uses Cartesia Sonic first.
    voice_agent_tts_provider: Literal["browser", "cartesia", "google", "system"] = "browser"
    google_tts_voice_name: str = "en-US-Chirp3-HD-Aoede"
    google_tts_language_code: str = "en-US"
    # Google Application Credentials path (optional — falls back to ADC)
    google_application_credentials: str = ""
    system_tts_voice_name: str = "Samantha"

    # Streaming STT/TTS — real adapters are key-gated with a mock fallback.
    deepgram_api_key: str = ""
    cartesia_api_key: str = ""
    cartesia_voice_id: str = "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"
    cartesia_voice_name: str = "Skylar"
    cartesia_tts_model: str = "sonic-3.5"
    cartesia_tts_language: str = "en"
    cartesia_tts_sample_rate: int = 44100
    cartesia_tts_container: str = "wav"
    cartesia_tts_encoding: str = "pcm_s16le"
    cartesia_tts_speed: float = 1.0
    cartesia_tts_volume: float = 1.0
    stt_mode: Literal["mock", "deepgram"] = "mock"
    tts_mode: Literal["mock", "cartesia", "browser", "system"] = "mock"

    # Voice runtime selector (Component 50).
    # "browser"     → use browser Web Speech API (default)
    # "gemini-live" → use Gemini Live when key is present; falls back to browser
    claimvoice_voice_runtime: Literal["browser", "gemini-live"] = "browser"
    gemini_api_key: str = ""          # server-side only — never exposed to frontend
    gemini_live_model: str = "gemini-3.1-flash-live-preview"
    gemini_live_voice: str = "Zephyr"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
