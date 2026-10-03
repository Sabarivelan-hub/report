"""Embedding generation service using Google Gemini text-embedding-004."""

import logging
from typing import List
import numpy as np
from google import genai

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages text embedding generation via Google Gemini API."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.client = genai.Client(api_key=self.api_key)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate a 768-dimensional embedding vector for a single text."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return [0.0] * self.dimension

        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=cleaned_text,
            )
            # Response contains embedding.values
            if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                vector = list(response.embedding.values)
                return self._normalize(vector)
            elif hasattr(response, "embeddings") and response.embeddings:
                vector = list(response.embeddings[0].values)
                return self._normalize(vector)
            else:
                logger.error(f"Unexpected embedding response structure: {response}")
                raise ValueError("Invalid response format from Gemini embed_content")
        except Exception as e:
            logger.error(f"Failed to generate embedding with Gemini: {str(e)}")
            raise

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """Generate embeddings for a list of text chunks in batches."""
        results: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            cleaned_batch = [t.strip() if t.strip() else " " for t in batch]

            try:
                # Gemini batch embedding
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=cleaned_batch,
                )
                if hasattr(response, "embeddings") and response.embeddings:
                    for emb in response.embeddings:
                        results.append(self._normalize(list(emb.values)))
                else:
                    # Fallback to single calls if batch format differs
                    for item in cleaned_batch:
                        results.append(self.generate_embedding(item))
            except Exception as e:
                logger.warning(f"Batch embedding failed, falling back to sequential: {e}")
                for item in cleaned_batch:
                    results.append(self.generate_embedding(item))

        return results

    @staticmethod
    def _normalize(vector: List[float]) -> List[float]:
        """L2 normalize vector for optimal cosine distance search."""
        arr = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return vector
        return (arr / norm).tolist()

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)


# Global singleton instance
embedding_service = EmbeddingService()
