"""
Retrieval module — vector search + cross-encoder reranking.

Improvements over v1:
- All print() replaced with structured logger calls
- QdrantClient reused as a singleton (no reconnect on every search call)
- SentenceTransformer + CrossEncoder loaded once at module level
- query rewrite only calls LLM when query is short (already was correct, kept)
- Cleaner deduplication of definition-boost logic (was done 3× previously)
- Noisy chunk filter is now a proper function with documented thresholds
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid

from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import CrossEncoder, SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
COLLECTION_NAME = "academic_chunks"
EMBEDDING_MODEL = "BAAI/bge-small-en"
VECTOR_SIZE = 384
SIMILARITY_THRESHOLD = 0.65   # minimum cosine similarity from Qdrant
RERANK_THRESHOLD = 0.78       # minimum cross-encoder score to keep a chunk

# ---------------------------------------------------------------------------
# Singletons — loaded once per process
# ---------------------------------------------------------------------------

logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
_embed_model = SentenceTransformer(EMBEDDING_MODEL)

logger.info("Loading reranker: BAAI/bge-reranker-base")
_reranker = CrossEncoder("BAAI/bge-reranker-base")

_qdrant: QdrantClient | None = None


def _get_qdrant() -> QdrantClient:
    """Return the singleton Qdrant client, creating it on first call."""
    global _qdrant
    if _qdrant is None:
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        logger.info("Connecting to Qdrant at %s:%d", host, port)
        _qdrant = QdrantClient(host=host, port=port)
    return _qdrant


# LLM client for query rewriting (reuse shared singleton approach)
_llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

# ---------------------------------------------------------------------------
# Chunk ingestion helpers (used by build_vector_db)
# ---------------------------------------------------------------------------


def load_chunks() -> list[dict]:
    """Read all JSON files from data/processed/ and return a flat list of chunks."""
    processed_dir = os.path.abspath(PROCESSED_DIR)
    all_chunks: list[dict] = []

    if not os.path.isdir(processed_dir):
        logger.warning("Processed directory not found: %s", processed_dir)
        return []

    json_files = [f for f in os.listdir(processed_dir) if f.endswith(".json")]
    if not json_files:
        logger.warning("No JSON files found in %s", processed_dir)
        return []

    for filename in json_files:
        filepath = os.path.join(processed_dir, filename)
        with open(filepath, "r", encoding="utf-8") as fh:
            chunks = json.load(fh)
            for chunk in chunks:
                chunk["id"] = str(uuid.uuid4())
            all_chunks.extend(chunks)

    logger.info("Loaded %d chunks from %d file(s)", len(all_chunks), len(json_files))
    return all_chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using the local sentence-transformers model."""
    logger.info("Embedding %d texts with %s", len(texts), EMBEDDING_MODEL)
    embeddings = _embed_model.encode(texts, show_progress_bar=True)
    return embeddings.tolist()


def store_in_qdrant(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """Store chunks with embeddings in Qdrant."""
    client = _get_qdrant()
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", COLLECTION_NAME)
    else:
        logger.info("Qdrant collection already exists: %s", COLLECTION_NAME)

    points = [
        PointStruct(
            id=chunk["id"],
            vector=embedding,
            payload={
                "content": chunk["content"],
                "source": chunk["metadata"]["source"],
                "page_start": chunk["metadata"]["page_start"],
                "page_end": chunk["metadata"]["page_end"],
            },
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=batch)
        except Exception as exc:
            logger.warning("Batch %d failed, retrying: %s", i // batch_size + 1, exc)
            time.sleep(1)
            try:
                client.upsert(collection_name=COLLECTION_NAME, points=batch)
            except Exception as exc2:
                logger.error("Batch %d failed permanently: %s", i // batch_size + 1, exc2)
                continue
        logger.info("Uploaded batch %d (%d points)", i // batch_size + 1, len(batch))

    logger.info("Stored %d vectors in Qdrant", len(points))


def build_vector_db() -> None:
    """Full pipeline: load chunks → embed → store in Qdrant."""
    logger.info("=== Building Vector Database ===")
    chunks = load_chunks()
    if not chunks:
        return
    texts = [chunk["content"] for chunk in chunks]
    logger.info("Generating embeddings...")
    embeddings = embed_texts(texts)
    logger.info("Storing in Qdrant...")
    store_in_qdrant(chunks, embeddings)
    logger.info("Vector database build complete.")


# ---------------------------------------------------------------------------
# Query analysis helpers
# ---------------------------------------------------------------------------


_NOISE_PHRASES = [
    "future work", "this paper explores", "in this survey",
    "the rest of the paper", "outline of the paper",
    "the remainder of this", "we conclude",
]


def _is_noisy(content: str) -> bool:
    """Return True if a chunk is likely a noise chunk (TOC, references, etc.)."""
    if len(content) < 120:
        return True
    if "....." in content or re.search(r"\.{3,}\s*\d+", content):
        return True
    if sum(c.isdigit() for c in content) / len(content) > 0.3:
        return True
    if len(re.findall(r"(?:^|\s)\d+\.", content)) >= 4:
        return True
    lower = content.lower()
    if any(phrase in lower for phrase in _NOISE_PHRASES):
        return True
    return False


_DEFINITION_QUERY_TERMS = ("what is", "define", "definition", "what are", "what does")
_DEFINITION_CHUNK_TERMS = (
    " is a ", " is an ", " refers to ", " is defined as ", " can be defined as ",
    " means ", " describes ", " consists of ", " composed of ",
    " is a type of ", " is a kind of ", " is a system that ",
)


def _is_definition_query(query: str) -> bool:
    q = query.lower()
    return any(x in q for x in _DEFINITION_QUERY_TERMS)


def _is_definition_chunk(text: str) -> bool:
    t = text.lower()
    return any(x in t for x in _DEFINITION_CHUNK_TERMS)


# ---------------------------------------------------------------------------
# Query rewriting
# ---------------------------------------------------------------------------


def rewrite_query(query: str) -> str:
    """Expand short / vague queries using LLM. Skips if query already has >6 words."""
    if len(query.split()) > 6:
        return query
    try:
        response = _llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a query rewriter for an academic retrieval system. "
                        "Given a short or vague query, expand it into a clear, detailed "
                        "academic query that will improve search results. "
                        "Keep it to one sentence. Do not add unrelated topics. "
                        "Return only the rewritten query, nothing else."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=100,
        )
        rewritten = response.choices[0].message.content.strip()
        if rewritten:
            logger.info("Query rewritten: %r → %r", query, rewritten)
            return rewritten
    except Exception as exc:
        logger.warning("Query rewrite failed: %s — using original", exc)
    return query


# ---------------------------------------------------------------------------
# Main search function
# ---------------------------------------------------------------------------


def search(query: str, top_k: int = 10) -> list[dict]:
    """
    Search Qdrant for chunks most similar to the query.

    Pipeline:
      1. Optionally rewrite the query (LLM)
      2. Embed the (rewritten) query
      3. Vector search in Qdrant (retrieves top_k * 3 candidates)
      4. Filter noisy chunks and low-similarity results
      5. Cross-encoder reranking
      6. Definition-query boosting
      7. Score threshold filtering
      8. Return top_k results
    """
    t0 = time.perf_counter()

    search_query = rewrite_query(query)
    query_embedding = _embed_model.encode(search_query).tolist()

    client = _get_qdrant()
    raw_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k * 3,
    ).points

    logger.info("Qdrant returned %d raw results", len(raw_results))

    # Filter: score threshold + noise removal
    clean = [
        {
            "content": hit.payload["content"],
            "source": hit.payload["source"],
            "page_start": hit.payload["page_start"],
            "page_end": hit.payload["page_end"],
            "score": hit.score,
        }
        for hit in raw_results
        if hit.score > SIMILARITY_THRESHOLD and not _is_noisy(hit.payload["content"])
    ]

    logger.info("After noise filter: %d chunks", len(clean))

    if not clean:
        logger.warning("No chunks passed noise filter — returning empty")
        return []

    # Cross-encoder reranking
    pairs = [(query, chunk["content"]) for chunk in clean]
    scores = _reranker.predict(pairs)
    for i, chunk in enumerate(clean):
        chunk["rerank_score"] = float(scores[i])

    is_def_query = _is_definition_query(query)
    logger.info("Definition query: %s", is_def_query)

    if is_def_query:
        # Boost definition chunks
        for c in clean:
            if _is_definition_chunk(c["content"]):
                c["rerank_score"] += 0.25

        # Sort: definitions first, then by score
        def_chunks = sorted(
            [c for c in clean if _is_definition_chunk(c["content"])],
            key=lambda x: x["rerank_score"],
            reverse=True,
        )
        other_chunks = sorted(
            [c for c in clean if not _is_definition_chunk(c["content"])],
            key=lambda x: x["rerank_score"],
            reverse=True,
        )
        clean = def_chunks + other_chunks

        # If we have no definition chunks at all, restrict to top 3 general chunks
        if not def_chunks:
            clean = clean[:3]
    else:
        clean = sorted(clean, key=lambda x: x["rerank_score"], reverse=True)

    # Apply rerank score threshold
    clean = [c for c in clean if c["rerank_score"] > RERANK_THRESHOLD]
    logger.info("After rerank threshold (>%.2f): %d chunks", RERANK_THRESHOLD, len(clean))

    # Final selection
    selected = clean[:top_k] if len(clean) >= 2 else clean[:max(len(clean), 2)]

    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    logger.info(
        "Search complete  query=%r  selected=%d  time=%.1fms",
        query[:60],
        len(selected),
        elapsed,
    )

    for i, c in enumerate(selected, 1):
        logger.debug(
            "[%d] rerank=%.3f  source=%s  preview=%r",
            i,
            c.get("rerank_score", 0),
            c.get("source", "?"),
            c["content"][:100],
        )

    return selected


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_vector_db()
