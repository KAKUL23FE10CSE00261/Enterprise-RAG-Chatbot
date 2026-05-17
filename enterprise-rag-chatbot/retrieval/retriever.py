"""
retrieval/retriever.py
Hybrid retrieval: dense vector search (ChromaDB) + BM25 keyword search,
fused with Reciprocal Rank Fusion, then reranked with Cohere v2.
"""

import os
import math
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_PATH    = "chroma_db"
COLLECTION_NAME = "enterprise_docs"
EMBED_MODEL    = "text-embedding-3-small"
TOP_K          = 12      # candidates for fusion
RERANK_TOP_N   = 5       # final chunks fed to LLM

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ── ChromaDB ──────────────────────────────────────────────────────────────────

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=EMBED_MODEL,
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
    )

# ── HyDE query rewriting ──────────────────────────────────────────────────────

def hyde_rewrite(query: str) -> str:
    """Generate a hypothetical answer paragraph to improve embedding alignment."""
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Write a short, factual paragraph that directly answers the following question. Be concise."},
            {"role": "user",   "content": query},
        ],
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()

# ── Vector search ─────────────────────────────────────────────────────────────

def vector_search(query: str, top_k: int = TOP_K,
                  doc_type_filter: str | None = None) -> list[dict]:
    """Dense semantic search with optional metadata filter."""
    collection = get_collection()
    where = {"doc_type": doc_type_filter} if doc_type_filter else None
    kwargs = dict(query_texts=[query], n_results=min(top_k, _collection_count(collection)))
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    return [
        {"text": doc, "source": meta.get("source", "unknown"),
         "filename": meta.get("filename", "unknown"),
         "doc_type": meta.get("doc_type", "general")}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

def _collection_count(col) -> int:
    try:
        return col.count()
    except Exception:
        return TOP_K

# ── BM25 keyword search ───────────────────────────────────────────────────────

def bm25_search(query: str, top_k: int = TOP_K,
                doc_type_filter: str | None = None) -> list[dict]:
    """Sparse keyword search over all stored chunks."""
    collection = get_collection()
    where = {"doc_type": doc_type_filter} if doc_type_filter else None
    kwargs = dict(include=["documents", "metadatas"])
    if where:
        kwargs["where"] = where

    data  = collection.get(**kwargs)
    docs  = data["documents"]
    metas = data["metadatas"]

    if not docs:
        return []

    tokenised = [d.lower().split() for d in docs]
    bm25      = BM25Okapi(tokenised)
    scores    = bm25.get_scores(query.lower().split())

    ranked = sorted(
        zip(scores, docs, metas), key=lambda x: x[0], reverse=True
    )[:top_k]

    return [
        {"text": doc, "source": meta.get("source", "unknown"),
         "filename": meta.get("filename", "unknown"),
         "doc_type": meta.get("doc_type", "general")}
        for _, doc, meta in ranked
    ]

# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results:   list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge two ranked lists using RRF. Higher score = more relevant."""
    scores: dict[str, float] = {}
    chunks: dict[str, dict]  = {}

    for rank, chunk in enumerate(vector_results):
        key = chunk["text"][:120]   # dedup key
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunks[key] = chunk

    for rank, chunk in enumerate(bm25_results):
        key = chunk["text"][:120]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunks[key] = chunk

    sorted_keys = sorted(scores, key=scores.__getitem__, reverse=True)
    return [chunks[k] for k in sorted_keys]

# ── Cohere reranker (v2 API) ──────────────────────────────────────────────────

def rerank(query: str, chunks: list[dict], top_n: int = RERANK_TOP_N) -> list[dict]:
    """Rerank with Cohere v2 API if key available, else return top-n by RRF."""
    cohere_key = os.environ.get("COHERE_API_KEY")
    if not cohere_key or not chunks:
        return chunks[:top_n]
    try:
        import cohere
        co = cohere.ClientV2(api_key=cohere_key)          # v2 client
        response = co.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=[c["text"] for c in chunks],
            top_n=top_n,
        )
        return [chunks[r.index] for r in response.results]
    except Exception as e:
        print(f"[reranker] Cohere error ({e}), falling back to RRF order.")
        return chunks[:top_n]

# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    use_hyde: bool = True,
    use_hybrid: bool = True,
    doc_type_filter: str | None = None,
) -> tuple[list[dict], str]:
    """
    Main retrieval entry point.
    Returns (chunks, search_query_used).
    """
    search_query = hyde_rewrite(query) if use_hyde else query

    if use_hybrid:
        vec   = vector_search(search_query, top_k=TOP_K, doc_type_filter=doc_type_filter)
        bm25  = bm25_search(query, top_k=TOP_K, doc_type_filter=doc_type_filter)
        fused = reciprocal_rank_fusion(vec, bm25)
    else:
        fused = vector_search(search_query, top_k=TOP_K, doc_type_filter=doc_type_filter)

    reranked = rerank(query, fused, top_n=RERANK_TOP_N)
    return reranked, search_query
