"""
High-level retrieval interface for the dissertation pipeline.

Builds a per-run BusinessKnowledgeStore from scenario source documents
and exposes a simple function to inject retrieved context into any agent prompt.
"""

from __future__ import annotations

from app.retrieval.store import BusinessKnowledgeStore


def build_store_from_scenario(scenario: dict) -> BusinessKnowledgeStore:
    """
    Construct and populate a BusinessKnowledgeStore from a scenario dict.

    The scenario must have a 'source_documents' list and a 'scenario_id' key.
    Each source document dict must have at least a 'text' field.
    """
    store = BusinessKnowledgeStore()
    docs = [
        {**doc, "business_id": scenario.get("scenario_id", "unknown")}
        for doc in scenario.get("source_documents", [])
    ]
    if docs:
        store.ingest(docs)
    return store


def get_retrieval_context(
    store: BusinessKnowledgeStore,
    agent_type: str,
    business_name: str = "",
    top_k: int = 5,
) -> str:
    """
    Retrieve relevant chunks for an agent and format them as a prompt context block.

    Returns an empty string when the store is not built (no source documents).
    """
    if not store.is_built:
        return ""

    results = store.retrieve_for_agent(agent_type, business_name)[:top_k]
    if not results:
        return ""

    lines = ["\n\n--- RETRIEVED BUSINESS CONTEXT (from source documents) ---"]
    for i, chunk in enumerate(results, 1):
        source = chunk.get("source_type", "unknown")
        score = chunk.get("score", 0.0)
        lines.append(f"[{i}] ({source}, relevance={score:.3f}): {chunk['text']}")
    lines.append("--- END RETRIEVED CONTEXT ---\n")
    return "\n".join(lines)
