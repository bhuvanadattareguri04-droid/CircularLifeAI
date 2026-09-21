"""
rag/retriever.py
----------------
In-memory RAG retriever for CircularLife AI.

How it works (step by step):
  1. Load recycle_guidelines.txt from the knowledge_base folder.
  2. Split the text into chunks — one chunk per paragraph block.
  3. Embed all chunks using sentence-transformers (done once, then cached).
  4. When the user provides an item description:
       a. Embed the description using the same model.
       b. Calculate cosine similarity between the description embedding
          and every chunk embedding.
       c. Select the top-K most similar chunks.
       d. Return them as a single string to be injected into the Groq prompt.

No external vector database, LangChain, Pinecone, FAISS, or Chroma is used.
Everything runs locally in memory.

Public functions:
    retrieve_context(query, top_k=3) -> str
    build_rag_context(query)         -> str   (formatted, ready for prompt)
"""

from __future__ import annotations

import os
import logging

import numpy as np

from rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

# ── Knowledge-base path ───────────────────────────────────────────────────────

# os.path.dirname(__file__) is the rag/ directory.
# The knowledge base lives at rag/knowledge_base/recycle_guidelines.txt
_KB_PATH = os.path.join(
    os.path.dirname(__file__),
    "knowledge_base",
    "recycle_guidelines.txt",
)

# ── Module-level cache ────────────────────────────────────────────────────────
# Both variables are populated on the first call to retrieve_context().
# After that they are reused for every subsequent call — no re-loading.

_chunks: list[str] = []            # list of text paragraphs from the knowledge base
_chunk_embeddings: np.ndarray | None = None  # numpy array, shape (N, embedding_dim)


# ── Step 1 & 2: load and split the knowledge base ────────────────────────────

def _load_chunks() -> list[str]:
    """Read recycle_guidelines.txt and split it into paragraph chunks.

    Each block of text separated by a blank line becomes one chunk.
    Empty blocks are discarded.
    """
    with open(_KB_PATH, encoding="utf-8") as f:
        text = f.read()

    # Split on blank lines (two or more newlines)
    raw_blocks = text.split("\n\n")

    # Strip whitespace and keep only non-empty blocks
    chunks = [block.strip() for block in raw_blocks if block.strip()]
    return chunks


# ── Step 3: embed all chunks and cache them ───────────────────────────────────

def _build_cache() -> bool:
    """Load chunks and compute their embeddings. Cache results in module globals.

    Returns True on success.
    Returns False on any error so that the caller can fall back gracefully.
    This function is called automatically on the first retrieve_context() call.
    """
    global _chunks, _chunk_embeddings

    # Already done — return immediately
    if _chunk_embeddings is not None:
        return True

    try:
        # Step 1 & 2: load and chunk the knowledge base
        _chunks = _load_chunks()

        if not _chunks:
            logger.warning("RAG: knowledge base is empty — RAG disabled.")
            return False

        # Step 3: embed all chunks at once (batch operation)
        model = get_embedding_model()
        _chunk_embeddings = model.encode(
            _chunks,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,
        )

        logger.info("RAG: cached %d knowledge-base chunks.", len(_chunks))
        return True

    except FileNotFoundError:
        logger.warning("RAG: knowledge base not found at: %s", _KB_PATH)
    except ImportError:
        logger.warning("RAG: sentence-transformers is not installed — RAG disabled.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG: failed to build cache — %s", exc)

    return False


# ── Step 4 & 5: cosine similarity ────────────────────────────────────────────

def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between one query vector and every row in matrix.

    Args:
        query_vec: 1-D array of shape (dim,) — the embedded user query.
        matrix:    2-D array of shape (N, dim) — all chunk embeddings.

    Returns:
        1-D array of shape (N,) with a similarity score in [-1, 1] for each chunk.
        Higher means more similar.
    """
    # L2-normalise the query vector
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)

    # L2-normalise each row of the chunk matrix
    row_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    matrix_norm = matrix / row_norms

    # Dot product of normalised vectors == cosine similarity
    return matrix_norm @ query_norm


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve_context(query: str, top_k: int = 3) -> str:
    """Retrieve the most relevant knowledge-base passages for the given query.

    This is the main function called by circular_life.py.

    Steps:
        1. Build the chunk cache on first call (lazy initialisation).
        2. Embed the user's query.
        3. Compute cosine similarity with all cached chunk embeddings.
        4. Return the top-K most relevant chunks joined by blank lines.

    Args:
        query: The user's item description.
        top_k: Number of chunks to return (default 3).

    Returns:
        A string containing the top-K relevant passages, or an empty string
        if RAG is unavailable (so the caller can fall back safely).
    """
    # Empty query — nothing to retrieve
    if not query.strip():
        return ""

    # Build the cache (no-op if already done)
    if not _build_cache():
        return ""  # RAG unavailable — caller continues without context

    try:
        model = get_embedding_model()

        # Step 4a: embed the user's query
        query_vec: np.ndarray = model.encode(
            query,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        # Step 4b & 5: compute similarity scores
        assert _chunk_embeddings is not None  # _build_cache() guarantees this
        scores: np.ndarray = _cosine_similarity(query_vec, _chunk_embeddings)

        # Step 6: select the top-K chunk indices (highest scores first)
        top_k = min(top_k, len(_chunks))
        top_indices = np.argsort(scores)[::-1][:top_k]

        # Step 7: collect and return the selected chunks
        selected = [_chunks[i] for i in top_indices]
        return "\n\n".join(selected)

    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG: retrieval failed — %s", exc)
        return ""


def build_rag_context(query: str) -> str:
    """Retrieve context and wrap it in labelled delimiters for prompt injection.

    Returns a formatted string like:

        --- Relevant circular-economy guidance ---
        <chunk 1>

        <chunk 2>

        <chunk 3>
        --- End of guidance ---

    Returns an empty string when no context is available, so the caller can
    simply check `if rag_context:` before using it.
    """
    raw = retrieve_context(query, top_k=3)
    if not raw:
        return ""

    return (
        "--- Relevant circular-economy guidance ---\n"
        f"{raw}\n"
        "--- End of guidance ---"
    )
