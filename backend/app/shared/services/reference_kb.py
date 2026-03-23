"""Global markdown reference KB with in-memory embeddings and retrieval."""

from __future__ import annotations

import math
import re
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.shared.services.openai_compatible import (
    create_sync_openai_client,
    get_embedding_model,
)

logger = get_logger("klarnow.reference_kb")
REPO_ROOT = Path(__file__).resolve().parents[4]
LEGACY_REFERENCE_DOC_PATHS = {
    "app/core/reference/100M-Leads.md": "backend/app/core/docs/100M-Leads.md",
    "app/core/docs/100M-Leads.md": "backend/app/core/docs/100M-Leads.md",
}
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")


@dataclass(slots=True)
class _Chunk:
    chunk_id: str
    heading: str
    text: str
    embedding: list[float]


class MarkdownReferenceKB:
    """Load, index, and retrieve context from one markdown reference document."""

    def __init__(self):
        settings = get_settings()
        self.enabled = settings.reference_doc_enabled
        self.reference_doc_path = settings.reference_doc_path
        self.embedding_model = get_embedding_model()
        self.chunk_chars = settings.reference_doc_chunk_chars
        self.chunk_overlap_chars = settings.reference_doc_chunk_overlap_chars
        self.top_k = settings.reference_doc_top_k
        self.min_score = settings.reference_doc_min_score
        self.max_chars = settings.reference_doc_max_chars
        self.cache_ttl_seconds = settings.reference_doc_cache_ttl_seconds

        self._client: OpenAI | None = None
        self._lock = threading.Lock()
        self._chunks: list[_Chunk] = []
        self._source_mtime: float | None = None
        self._source_path: str | None = None
        self._last_checked_at = 0.0

    def warmup(self) -> None:
        """Best-effort prewarm for startup; never raises."""
        if not self.enabled:
            logger.info("reference_kb_warmup_skip | enabled=false")
            return
        try:
            self._maybe_refresh_index(force=True)
        except Exception as e:
            logger.warning("reference_kb_warmup_error | error=%s", e)

    def retrieve(self, query: str) -> dict[str, Any]:
        """Retrieve top-k markdown chunks relevant to the user query."""
        if not self.enabled or not query.strip():
            return {"context_text": "", "references": []}

        try:
            self._maybe_refresh_index(force=False)
        except Exception as e:
            logger.warning("reference_kb_refresh_error | error=%s", e)
            return {"context_text": "", "references": []}

        with self._lock:
            chunks = list(self._chunks)
        if not chunks:
            return {"context_text": "", "references": []}

        query_embedding = self._embed_query(query)
        if not query_embedding:
            return {"context_text": "", "references": []}

        scored: list[tuple[float, _Chunk]] = []
        for chunk in chunks:
            score = self._cosine_similarity(query_embedding, chunk.embedding)
            if score >= self.min_score:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: max(1, self.top_k)]

        references: list[dict[str, Any]] = []
        context_parts: list[str] = []
        for score, chunk in top:
            excerpt = self._compact_whitespace(chunk.text)
            excerpt = excerpt[:280] if len(excerpt) > 280 else excerpt
            references.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "score": round(float(score), 4),
                    "excerpt": excerpt,
                }
            )
            heading = chunk.heading or "Reference"
            context_parts.append(f"[{chunk.chunk_id}] {heading}\n{chunk.text}")

        top_score = top[0][0] if top else 0.0
        logger.info(
            "reference_kb_retrieval | hits=%s | top_score=%.4f | query_chars=%s",
            len(references),
            top_score,
            len(query),
        )
        return {"context_text": "\n\n---\n\n".join(context_parts), "references": references}

    def _maybe_refresh_index(self, *, force: bool) -> None:
        now = time.time()
        with self._lock:
            if not force and (now - self._last_checked_at) < max(1, self.cache_ttl_seconds):
                return
            self._last_checked_at = now

        path = self._resolve_path()
        if not path:
            logger.warning("reference_kb_disabled_or_missing_path")
            with self._lock:
                self._chunks = []
                self._source_mtime = None
                self._source_path = None
            return

        if path.suffix.lower() != ".md":
            logger.warning(
                "reference_kb_invalid_extension | path=%s | expected=.md",
                str(path),
            )
            with self._lock:
                self._chunks = []
                self._source_mtime = None
                self._source_path = str(path)
            return

        if not path.exists() or not path.is_file():
            logger.warning("reference_kb_file_missing | path=%s", str(path))
            with self._lock:
                self._chunks = []
                self._source_mtime = None
                self._source_path = str(path)
            return

        mtime = path.stat().st_mtime
        with self._lock:
            if not force and self._source_mtime == mtime and self._chunks:
                return

        text = path.read_text(encoding="utf-8", errors="ignore")
        if len(text) > self.max_chars:
            logger.info(
                "reference_kb_text_truncated | path=%s | original_chars=%s | kept_chars=%s",
                str(path),
                len(text),
                self.max_chars,
            )
            text = text[: self.max_chars]

        sections = self._split_markdown_sections(text)
        chunk_inputs = self._chunk_sections(sections)
        if not chunk_inputs:
            logger.warning("reference_kb_no_chunks | path=%s", str(path))
            with self._lock:
                self._chunks = []
                self._source_mtime = mtime
                self._source_path = str(path)
            return

        embeddings = self._embed_texts([chunk_text for _, chunk_text in chunk_inputs])
        if not embeddings or len(embeddings) != len(chunk_inputs):
            logger.warning(
                "reference_kb_embedding_failed | path=%s | chunks=%s | embeddings=%s",
                str(path),
                len(chunk_inputs),
                len(embeddings),
            )
            with self._lock:
                self._chunks = []
                self._source_mtime = mtime
                self._source_path = str(path)
            return

        indexed_chunks: list[_Chunk] = []
        for idx, ((heading, chunk_text), embedding) in enumerate(
            zip(chunk_inputs, embeddings),
            start=1,
        ):
            indexed_chunks.append(
                _Chunk(
                    chunk_id=f"ref-{idx}",
                    heading=heading,
                    text=chunk_text,
                    embedding=embedding,
                )
            )

        with self._lock:
            self._chunks = indexed_chunks
            self._source_mtime = mtime
            self._source_path = str(path)
        logger.info(
            "reference_kb_index_built | path=%s | chunks=%s | mtime=%s",
            str(path),
            len(indexed_chunks),
            int(mtime),
        )

    def _resolve_path(self) -> Path | None:
        if not self.enabled:
            return None
        if not self.reference_doc_path:
            return None
        path = Path(self.reference_doc_path).expanduser()
        if path.is_absolute():
            return path

        repo_relative_path = REPO_ROOT / path
        if repo_relative_path.exists():
            return repo_relative_path

        normalized = path.as_posix()
        legacy_path = LEGACY_REFERENCE_DOC_PATHS.get(normalized)
        if legacy_path:
            return REPO_ROOT / legacy_path

        if normalized.startswith("app/"):
            return REPO_ROOT / "backend" / normalized

        path = repo_relative_path
        return path

    def _get_client(self) -> OpenAI | None:
        if self._client:
            return self._client
        client = create_sync_openai_client()
        if not client:
            logger.warning("reference_kb_ai_key_missing")
            return None
        self._client = client
        return self._client

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        if not client or not texts:
            return []

        vectors: list[list[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.embeddings.create(
                model=self.embedding_model,
                input=batch,
            )
            rows = sorted(response.data, key=lambda row: row.index)
            vectors.extend([row.embedding for row in rows])
        return vectors

    def _embed_query(self, query: str) -> list[float] | None:
        client = self._get_client()
        if not client:
            return None
        try:
            response = client.embeddings.create(
                model=self.embedding_model,
                input=query,
            )
            if not response.data:
                return None
            return response.data[0].embedding
        except Exception as e:
            logger.warning("reference_kb_query_embedding_failed | error=%s", e)
            return None

    def _split_markdown_sections(self, text: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        current_heading = "Document"
        current_lines: list[str] = []
        for line in text.splitlines():
            match = HEADING_RE.match(line)
            if match:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append((current_heading, body))
                current_heading = match.group(2).strip() or "Section"
                current_lines = []
                continue
            current_lines.append(line)
        tail = "\n".join(current_lines).strip()
        if tail:
            sections.append((current_heading, tail))
        return sections

    def _chunk_sections(self, sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
        chunks: list[tuple[str, str]] = []
        for heading, body in sections:
            for part in self._split_text_with_overlap(body):
                chunks.append((heading, part))
        return chunks

    def _split_text_with_overlap(self, text: str) -> list[str]:
        cleaned = text.strip()
        if not cleaned:
            return []
        if len(cleaned) <= self.chunk_chars:
            return [cleaned]

        out: list[str] = []
        start = 0
        text_len = len(cleaned)
        overlap = min(max(0, self.chunk_overlap_chars), max(0, self.chunk_chars - 1))
        while start < text_len:
            hard_end = min(start + self.chunk_chars, text_len)
            end = hard_end
            if hard_end < text_len:
                window = cleaned[start:hard_end]
                break_idx = max(
                    window.rfind("\n\n"),
                    window.rfind(". "),
                    window.rfind("\n"),
                )
                if break_idx >= max(200, len(window) // 2):
                    end = start + break_idx + 1

            chunk = cleaned[start:end].strip()
            if chunk:
                out.append(chunk)
            if end >= text_len:
                break
            next_start = max(0, end - overlap)
            if next_start <= start:
                next_start = end
            start = next_start
        return out

    @staticmethod
    def _compact_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


@lru_cache
def get_reference_kb() -> MarkdownReferenceKB:
    return MarkdownReferenceKB()
