"""Hybrid search wrapper with OpenRouter embeddings."""
import os
from openai import OpenAI
from typing import List, Tuple
from .database import VeloDBClient


class HybridSearch:
    """Wrapper for hybrid search using VeloDB and OpenRouter embeddings."""

    def __init__(self):
        """Initialize VeloDB client and OpenRouter API."""
        self.db = VeloDBClient()
        self.client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )

    def embed(self, text: str) -> List[float]:
        """Generate embeddings using OpenRouter."""
        response = self.client.embeddings.create(
            model="openai/text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def search(self, query: str, top_k: int = 5) -> List[Tuple]:
        """Search using hybrid search."""
        embedding = self.embed(query)
        return self.db.hybrid_search(query, embedding, top_k)

    def ingest(self, content: str, chunk_size: int = 512):
        """Ingest a document by chunking and embedding."""
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        for chunk in chunks:
            if chunk.strip():
                embedding = self.embed(chunk)
                self.db.insert(chunk, embedding)

    def close(self):
        """Close database connection."""
        self.db.close()
