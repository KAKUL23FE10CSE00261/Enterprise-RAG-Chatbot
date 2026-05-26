"""
retrieval/retriever.py

Fixes applied:
  1. ChromaDB singleton client — one client per process, not one per call
  2. BM25 index cached in memory — invalidated when collection count changes
  3. TOP_K / RERANK_TOP_N configurable via env vars
  4. All public constants exposed for testing
"""

import os
import threading
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from groq import Groq

CHROMA_PATH     = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "enterprise_docs"
TOP_K           = int(os.environ.get("RAG_TOP_K", 12))
RERANK_TOP_N    = int(os.environ.get("RAG_RERANK_TOP_N", 5))

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# ── ChromaDB singleton ────────────────────────────────────────────────────────
# One persistent client per process avoids repeated filesystem opens.
_chroma_client: chromadb.PersistentClient | None = None
_chroma_lock   = threading.Lock()


def _get_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def get_collection():
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def invalidate_collection_cache() -> None:
    """
    Call this after ingesting or deleting documents so the BM25 cache
    is rebuilt on the next query.  Also resets the ChromaDB client so
    it re-reads the updated sqlite3 file.
    """
    global _chroma_client
    with _chroma_lock:
        _chroma_client = None
    _bm25_cache.clear()


# ── BM25 cache ────────────────────────────────────────────────────────────────
# Key: (doc_type_filter or "all", collection_count)
# Value: (BM25Okapi index, list[str] docs, list[dict] metadatas)
# When the collection grows/shrinks the count changes → automatic invalidation.
_bm25_cache: dict = {}
_bm25_lock  = threading.Lock()


def _get_bm25_index(collection, doc_type_filter=None):
    count = _collection_count(collection)
    cache_key = (doc_type_filter or "all", count)

    with _bm25_lock:
        if cache_key in _bm25_cache:
            return _bm25_cache[cache_key]

        # Build index
        where  = {"doc_type": doc_type_filter} if doc_type_filter else None
        kwargs = dict(include=["documents", "metadatas"])
        if where:
            kwargs["where"] = where
        data  = collection.get(**kwargs)
        docs  = data["documents"] or []
        metas = data["metadatas"] or []

        if not docs:
            _bm25_cache[cache_key] = (None, [], [])
            return _bm25_cache[cache_key]

        tokenised = [d.lower().split() for d in docs]
        index     = BM25Okapi(tokenised)
        _bm25_cache[cache_key] = (index, docs, metas)
        return _bm25_cache[cache_key]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _collection_count(col) -> int:
    try:
        return max(col.count(), 1)
    except Exception:
        return TOP_K


def hyde_rewrite(query: str) -> str:
    """Generate a hypothetical answer and use it as the search query (HyDE)."""
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Write a short factual paragraph answering this question:"},
                {"role": "user",   "content": query},
            ],
            max_tokens=150,
            timeout=10,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return query


# ── Search functions ──────────────────────────────────────────────────────────

def vector_search(query: str, top_k=TOP_K, doc_type_filter=None) -> list[dict]:
    collection = get_collection()
    count      = _collection_count(collection)
    if count == 0:
        return []
    where  = {"doc_type": doc_type_filter} if doc_type_filter else None
    kwargs = dict(query_texts=[query], n_results=min(top_k, count))
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    return [
        {
            "text":     doc,
            "source":   meta.get("source", ""),
            "filename": meta.get("filename", "unknown"),
            "doc_type": meta.get("doc_type", "general"),
        }
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def bm25_search(query: str, top_k=TOP_K, doc_type_filter=None) -> list[dict]:
    """
    BM25 search using cached index — O(1) corpus load after first call.
    Index is rebuilt only when collection count changes.
    """
    collection = get_collection()
    index, docs, metas = _get_bm25_index(collection, doc_type_filter)

    if index is None or not docs:
        return []

    scores = index.get_scores(query.lower().split())
    ranked = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)[:top_k]
    return [
        {
            "text":     doc,
            "source":   meta.get("source", ""),
            "filename": meta.get("filename", "unknown"),
            "doc_type": meta.get("doc_type", "general"),
        }
        for _, doc, meta in ranked
    ]


def reciprocal_rank_fusion(
    vector_results: list, bm25_results: list, k: int = 60
) -> list[dict]:
    scores: dict[str, float] = {}
    chunks: dict[str, dict]  = {}
    for rank, chunk in enumerate(vector_results):
        key            = chunk["text"][:120]
        scores[key]    = scores.get(key, 0) + 1 / (k + rank + 1)
        chunks[key]    = chunk
    for rank, chunk in enumerate(bm25_results):
        key            = chunk["text"][:120]
        scores[key]    = scores.get(key, 0) + 1 / (k + rank + 1)
        chunks[key]    = chunk
    return [chunks[k] for k in sorted(scores, key=scores.__getitem__, reverse=True)]


def rerank(query: str, chunks: list, top_n=RERANK_TOP_N) -> list[dict]:
    key = os.environ.get("COHERE_API_KEY")
    if not key or not chunks:
        return chunks[:top_n]
    try:
        import cohere
        co       = cohere.ClientV2(api_key=key)
        response = co.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=[c["text"] for c in chunks],
            top_n=top_n,
        )
        return [chunks[r.index] for r in response.results]
    except Exception as e:
        print(f"[reranker] Cohere error: {e}")
        return chunks[:top_n]


# ── Main retrieve entry point ─────────────────────────────────────────────────

def retrieve(
    query: str,
    use_hyde: bool   = True,
    use_hybrid: bool = True,
    doc_type_filter  = None,
    top_k: int       = TOP_K,
    rerank_top_n: int = RERANK_TOP_N,
) -> tuple[list[dict], str]:
    search_query = hyde_rewrite(query) if use_hyde else query

    if use_hybrid:
        vec   = vector_search(search_query, top_k, doc_type_filter)
        bm25  = bm25_search(query, top_k, doc_type_filter)
        fused = reciprocal_rank_fusion(vec, bm25)
    else:
        fused = vector_search(search_query, top_k, doc_type_filter)

    return rerank(query, fused, rerank_top_n), search_query