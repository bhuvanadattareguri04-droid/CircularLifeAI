"""
rag/embeddings.py
-----------------
Loads and caches the sentence-transformer embedding model.

The model (all-MiniLM-L6-v2) is small (~80 MB) and is downloaded
automatically by sentence-transformers the first time it is used.
After that, it is stored in the local HuggingFace cache and loaded
from disk on subsequent runs — no manual download needed.

Key design decision: the model is stored in the module-level variable
_model so it is initialised ONCE per process and reused for every call
to retrieve_context(). This avoids paying the load cost on every query.
"""

from __future__ import annotations

# _model holds the loaded SentenceTransformer instance.
# It starts as None and is populated on the first call to get_embedding_model().
_model = None

# Name of the embedding model to use.
# all-MiniLM-L6-v2 is lightweight, fast, and works well for semantic similarity.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def get_embedding_model():
    """Return the cached SentenceTransformer model.

    On the first call this loads (and possibly downloads) the model.
    On every subsequent call it returns the already-loaded instance immediately.

    Returns:
        SentenceTransformer: the loaded embedding model.
    """
    global _model

    if _model is None:
        # Imported inside the function so that a missing sentence-transformers
        # package only raises an error when RAG is actually attempted,
        # not at application start-up.
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _model
