"""Embedding helper for SBC RAG.

Dispatches to Azure OpenAI `text-embedding-3-large` (default) or Voyage (fallback)
based on `settings.sbc_embed_provider`. The query and the ingest must use the same
model + dimensions; the ingest mirrors this logic in `data/ingest/sbc_embed_ingest.py`.
"""

from __future__ import annotations

from eligibility.core.config import settings


def embed_query(text: str) -> list[float]:
    """Embed a single query string; returns one vector."""
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via the configured provider."""
    if settings.sbc_embed_provider.lower() == "azure":
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
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
