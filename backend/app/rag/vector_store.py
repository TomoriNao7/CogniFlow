"""Milvus Lite vector store — embedded, no server needed."""

from __future__ import annotations

import os
from typing import Any

from pymilvus import (
    Collection,
    DataType,
    FieldSchema,
    CollectionSchema,
    MilvusClient,
    connections,
    utility,
)

from app.config import settings

# Milvus Lite uses a local file for storage
DEFAULT_URI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", ".milvus", "cogniflow.db",
)
DIM = 1024  # text-embedding-v3 dimension
COLLECTION = settings.milvus_collection


class VectorStore:
    """Wraps Milvus Lite for chunk storage and semantic search."""

    def __init__(self, uri: str | None = None) -> None:
        self.uri = uri or DEFAULT_URI
        self._client: MilvusClient | None = None
        self._collection_ready = False

    @property
    def client(self) -> MilvusClient:
        if self._client is None:
            os.makedirs(os.path.dirname(self.uri), exist_ok=True)
            self._client = MilvusClient(uri=self.uri)
        return self._client

    def create_collection(self, drop_existing: bool = False) -> None:
        """Create the knowledge_chunks collection with schema."""
        if drop_existing and self.client.has_collection(COLLECTION):
            self.client.drop_collection(COLLECTION)

        if self.client.has_collection(COLLECTION):
            self._collection_ready = True
            return

        schema = CollectionSchema(
            fields=[
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="source_document", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="heading", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
            ],
            description="CogniFlow knowledge base chunks",
        )

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=COLLECTION,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(COLLECTION)
        self._collection_ready = True

    def insert(self, rows: list[dict[str, Any]]) -> int:
        """Insert chunk records. Each row: chunk_id, content, source_document, heading, chunk_index, embedding."""
        if not rows:
            return 0
        result = self.client.insert(collection_name=COLLECTION, data=rows)
        return result["insert_count"]

    def load(self) -> None:
        """Load collection into memory (required before search)."""
        if self.client.has_collection(COLLECTION):
            self.client.load_collection(COLLECTION)

    def search(
        self, query_vector: list[float], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Semantic search — returns top_k matched chunks with metadata."""
        self.load()  # ensure collection is in memory (idempotent)
        results = self.client.search(
            collection_name=COLLECTION,
            data=[query_vector],
            limit=top_k,
            output_fields=["chunk_id", "content", "source_document", "heading"],
        )
        return results[0] if results else []

    @property
    def is_ready(self) -> bool:
        return self._collection_ready or self.client.has_collection(COLLECTION)


# Singleton
vector_store = VectorStore()
