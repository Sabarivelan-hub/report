"""Configurable document text chunker preserving semantic boundaries and metadata."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.config import settings


class Chunk(BaseModel):
    """Represents an individual chunk of text along with preserved metadata."""
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    char_length: int
    token_estimate: int


class TextChunker:
    """Splits long text documents into overlapping semantic chunks."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size or settings.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")

    def split_text(self, text: str) -> List[str]:
        """Recursively split text into segments satisfying chunk_size and chunk_overlap."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        return self._recursive_split(text, self.separators)

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """Split text using the highest priority separator that yields sub-chunks."""
        final_chunks: List[str] = []

        # Find best separator
        separator = separators[-1]
        new_separators = []
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)

        # Merge splits into chunks adhering to chunk_size and overlap
        current_chunk: List[str] = []
        current_len = 0

        for split in splits:
            split_len = len(split) + (len(separator) if current_chunk else 0)

            if current_len + split_len > self.chunk_size:
                if current_chunk:
                    chunk_str = separator.join(current_chunk).strip()
                    if chunk_str:
                        final_chunks.append(chunk_str)

                    # Calculate overlap: backtrack elements
                    overlap_chunk: List[str] = []
                    overlap_len = 0
                    for prev_split in reversed(current_chunk):
                        if overlap_len + len(prev_split) <= self.chunk_overlap:
                            overlap_chunk.insert(0, prev_split)
                            overlap_len += len(prev_split) + len(separator)
                        else:
                            break

                    current_chunk = overlap_chunk
                    current_len = sum(len(s) for s in current_chunk) + (
                        len(separator) * (len(current_chunk) - 1) if current_chunk else 0
                    )

                # If a single split segment is itself larger than chunk_size, split further
                if len(split) > self.chunk_size:
                    if new_separators:
                        sub_chunks = self._recursive_split(split, new_separators)
                        final_chunks.extend(sub_chunks)
                    else:
                        # Hard character boundary
                        for j in range(0, len(split), self.chunk_size - self.chunk_overlap):
                            final_chunks.append(split[j : j + self.chunk_size])
                else:
                    current_chunk.append(split)
                    current_len += len(split) + (len(separator) if len(current_chunk) > 1 else 0)
            else:
                current_chunk.append(split)
                current_len += split_len

        if current_chunk:
            last_chunk = separator.join(current_chunk).strip()
            if last_chunk:
                final_chunks.append(last_chunk)

        return final_chunks

    def chunk_document(
        self,
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Process a full document into metadata-tagged Chunk objects."""
        raw_chunks = self.split_text(text)
        base_meta = document_metadata or {}
        total_chunks = len(raw_chunks)

        chunks: List[Chunk] = []
        for idx, content in enumerate(raw_chunks):
            chunk_meta = {
                **base_meta,
                "chunk_index": idx,
                "total_chunks": total_chunks,
            }
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    content=content,
                    metadata=chunk_meta,
                    char_length=len(content),
                    token_estimate=max(1, len(content) // 4),  # Standard 4 chars per token rule-of-thumb
                )
            )

        return chunks
