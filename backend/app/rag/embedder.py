"""Embedding service — wraps dashscope text-embedding-v3 via OpenAI-compatible API."""

from __future__ import annotations

from app.config import settings


class Embedder:
    """Text embedder using dashscope / OpenAI-compatible API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or settings.embedding_model
        self._api_key = api_key or settings.qwen_api_key
        self._base_url = base_url or settings.qwen_base_url
        self._client: object = None

    @property
    def _openai_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    def embed(self, texts: str | list[str]) -> list[list[float]]:
        """Embed one or multiple texts. Returns list of vectors (1024-dim)."""
        if isinstance(texts, str):
            texts = [texts]

        resp = self._openai_client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [d.embedding for d in resp.data]

    def embed_query(self, query: str) -> list[float]:
        """Convenience: embed a single query string."""
        return self.embed(query)[0]


# Singleton
embedder = Embedder()
