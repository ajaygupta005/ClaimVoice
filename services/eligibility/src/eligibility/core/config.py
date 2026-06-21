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

    voyage_api_key: str = ""  # SBC RAG embeddings — Voyage fallback provider

    # SBC RAG embeddings — provider + Azure OpenAI creds (active by default).
    sbc_embed_provider: Literal["azure", "voyage"] = "azure"
    embedding_dimensions: int = 1024
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    foundry_deployment_embedding: str = "text-embedding-3-large"

    # SBC RAG enrichment of coverage answers (best-effort; off when no embed key).
    sbc_rag_in_coverage: bool = True
    sbc_rag_top_k: int = 2

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
