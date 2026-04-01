"""
FAISS-based vector store for business knowledge retrieval.

Demonstrates: vector indexing, efficient approximate nearest-neighbour
search, knowledge grounding for LLM prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from app.retrieval.embedder import embed_texts
from app.retrieval.preprocessor import chunk_document, clean_text


class BusinessKnowledgeStore:
    """
    Vector store for business source documents.

    Indexes chunked business documents using sentence-BERT embeddings
    and FAISS for efficient similarity search. Supports task-specific
    retrieval tailored to different agents in the pipeline.
    """

    def __init__(self) -> None:
        self.index = None          # faiss.IndexFlatIP — inner product on normalised vecs = cosine
        self.chunks: list[str] = []
        self.metadata: list[dict] = []
        self.is_built = False

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(self, documents: list[dict], chunk_size: int = 400) -> dict:
        """
        Ingest source documents into the vector store.

        Args:
            documents: List of dicts with keys:
                - text (str): document content
                - source_type (str): e.g. 'brief', 'services', 'testimonials'
                - business_id (str): identifier for the business
            chunk_size: Target token count per chunk.

        Returns:
            Summary dict with total_documents, total_chunks, embedding_dimension.
        """
        import faiss  # import here so the module loads without faiss installed

        all_chunks: list[str] = []
        all_metadata: list[dict] = []

        for doc in documents:
            text = clean_text(doc.get("text", "") or "")
            source_type = doc.get("source_type", "unknown")
            business_id = doc.get("business_id", "unknown")

            for chunk in chunk_document(text, chunk_size=chunk_size):
                all_chunks.append(chunk["text"])
                all_metadata.append(
                    {
                        "source_type": source_type,
                        "business_id": business_id,
                        "chunk_index": chunk["chunk_index"],
                        "token_count": chunk["token_count"],
                    }
                )

        if not all_chunks:
            raise ValueError("No chunks produced from documents")

        self.chunks = all_chunks
        self.metadata = all_metadata

        embeddings = embed_texts(all_chunks).astype("float32")

        # Normalise for cosine similarity via inner product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        self.is_built = True

        return {
            "total_documents": len(documents),
            "total_chunks": len(all_chunks),
            "embedding_dimension": dimension,
        }

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Retrieve the most semantically relevant chunks for a query.

        Args:
            query: Natural language query.
            top_k: Number of chunks to return.

        Returns:
            List of dicts with text, score, source_type, etc.
        """
        if not self.is_built or self.index is None:
            raise RuntimeError("Store not built. Call ingest() first.")

        query_embedding = embed_texts([query]).astype("float32")
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm

        k = min(top_k, len(self.chunks))
        scores, indices = self.index.search(query_embedding, k)

        results: list[dict] = []
        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(self.chunks):
                results.append(
                    {
                        "text": self.chunks[idx],
                        "score": round(float(scores[0][i]), 4),
                        **self.metadata[idx],
                    }
                )

        return results

    def retrieve_for_agent(self, agent_type: str, business_context: str = "") -> list[dict]:
        """
        Task-specific retrieval tailored to each agent's information needs.

        Different agents benefit from different retrieval queries:
        - strategy  → positioning, audience, market differentiation
        - identity  → tone, visual style, brand personality
        - website   → services, offers, trust signals, CTA
        - creative  → campaign hooks, emotional drivers, offers
        - qa        → core brand message, consistency anchors
        """
        queries: dict[str, str] = {
            "strategy": (
                f"business positioning target audience value proposition "
                f"market differentiation {business_context}"
            ),
            "identity": (
                f"brand personality visual style tone of voice creative direction "
                f"{business_context}"
            ),
            "website": (
                f"services offered pricing structure call to action trust signals "
                f"testimonials {business_context}"
            ),
            "creative": (
                f"campaign messaging emotional hooks audience pain points "
                f"promotional offers {business_context}"
            ),
            "qa": (
                f"brand strategy core message target audience key differentiators "
                f"{business_context}"
            ),
        }
        query = queries.get(agent_type, business_context or "business overview")
        return self.retrieve(query, top_k=5)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist the FAISS index and chunk metadata to disk."""
        import faiss

        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(dir_path / "index.faiss"))
        with open(dir_path / "chunks.json", "w") as f:
            json.dump({"chunks": self.chunks, "metadata": self.metadata}, f)

    def load(self, path: str) -> None:
        """Load a previously saved FAISS index and chunk metadata from disk."""
        import faiss

        dir_path = Path(path)
        self.index = faiss.read_index(str(dir_path / "index.faiss"))
        with open(dir_path / "chunks.json") as f:
            data = json.load(f)
        self.chunks = data["chunks"]
        self.metadata = data["metadata"]
        self.is_built = True
