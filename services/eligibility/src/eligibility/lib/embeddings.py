"""Embedding helper for SBC RAG.

Dispatches to Azure OpenAI or Voyage based on configured credentials. The query and
ingest must use compatible dimensions; local demos usually use Voyage because that is
the key developers are expected to provision.
"""

from __future__ import annotations

from eligibility.core.config import settings


class EmbeddingProviderUnavailable(RuntimeError):
    """Raised when no embedding provider has usable credentials."""


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _azure_configured() -> bool:
    return bool(
        _clean(getattr(settings, "azure_openai_endpoint", ""))
        and _clean(getattr(settings, "azure_openai_api_key", ""))
    )


def _voyage_configured() -> bool:
    return bool(_clean(getattr(settings, "voyage_api_key", "")))


def active_embedding_provider() -> str:
    """Return the provider the runtime can actually call.

    Historically the default was ``azure`` while local setup instructions asked
    developers to configure ``VOYAGE_API_KEY``. That made readiness green but
    retrieval fail at runtime. Prefer the requested provider when it is fully
    configured, then fall back to whichever provider has credentials.
    """
    requested = _clean(getattr(settings, "sbc_embed_provider", "azure")).lower() or "azure"
    azure_ready = _azure_configured()
    voyage_ready = _voyage_configured()

    if requested == "azure" and azure_ready:
        return "azure"
    if requested == "voyage" and voyage_ready:
        return "voyage"
    if voyage_ready:
        return "voyage"
    if azure_ready:
        return "azure"

    raise EmbeddingProviderUnavailable(
        "No SBC embedding provider is configured. Set VOYAGE_API_KEY or Azure OpenAI embedding credentials."
    )


def embed_query(text: str) -> list[float]:
    """Embed a single query string; returns one vector."""
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via the configured provider."""
    provider = active_embedding_provider()
    if provider == "azure":
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            timeout=4.0,      # bound per-request latency (SDK default is ~600s)
            max_retries=0,    # never let a slow embed hang the /coverage request
        )
        resp = client.embeddings.create(
            input=texts,
            model=settings.foundry_deployment_embedding,
            dimensions=settings.embedding_dimensions,
        )
        return [d.embedding for d in resp.data]

    import voyageai

    client = voyageai.Client(api_key=settings.voyage_api_key)
    result = client.embed(texts, model="voyage-4-large", input_type="query")
    return result.embeddings
