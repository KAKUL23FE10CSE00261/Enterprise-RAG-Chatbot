"""
retrieval/retriever.py
Hybrid retrieval: dense vector (SentenceTransformer) + BM25 + RRF + Cohere reranker.
HyDE rewriting uses Groq (free).
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from groq import Groq

CHROMA_PATH     = "chroma_db"
COLLECTION_NAME = "enterprise_docs"
TOP_K           = 12
RERANK_TOP_N    = 5

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
    )


def hyde_rewrite(query):
    """Generate a hypothetical answer using Groq to improve retrieval."""
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Write a short factual paragraph answering this question:"},
                {"role": "user",   "content": query},
            ],
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return query  # fallback to original query


def _collection_count(col):
    try:
        return max(col.count(), 1)
    except Exception:
        return TOP_K


def vector_search(query, top_k=TOP_K, doc_type_filter=None):
    collection = get_collection()
    count = _collection_count(collection)
    if count == 0:
        return []
    where  = {"doc_type": doc_type_filter} if doc_type_filter else None
    kwargs = dict(query_texts=[query], n_results=min(top_k, count))
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    return [
        {"text": doc, "source": meta.get("source", ""),
         "filename": meta.get("filename", "unknown"),
         "doc_type": meta.get("doc_type", "general")}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def bm25_search(query, top_k=TOP_K, doc_type_filter=None):
    collection = get_collection()
    where  = {"doc_type": doc_type_filter} if doc_type_filter else None
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
    ranked    = sorted(zip(scores, docs, metas), key=lambda x: x[0], reverse=True)[:top_k]
    return [
        {"text": doc, "source": meta.get("source", ""),
         "filename": meta.get("filename", "unknown"),
         "doc_type": meta.get("doc_type", "general")}
        for _, doc, meta in ranked
    ]


def reciprocal_rank_fusion(vector_results, bm25_results, k=60):
    scores, chunks = {}, {}
    for rank, chunk in enumerate(vector_results):
        key = chunk["text"][:120]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunks[key] = chunk
    for rank, chunk in enumerate(bm25_results):
        key = chunk["text"][:120]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunks[key] = chunk
    return [chunks[k] for k in sorted(scores, key=scores.__getitem__, reverse=True)]


def rerank(query, chunks, top_n=RERANK_TOP_N):
    key = os.environ.get("COHERE_API_KEY")
    if not key or not chunks:
        return chunks[:top_n]
    try:
        import cohere
        co       = cohere.ClientV2(api_key=key)
        response = co.rerank(model="rerank-english-v3.0", query=query,
                             documents=[c["text"] for c in chunks], top_n=top_n)
        return [chunks[r.index] for r in response.results]
    except Exception as e:
        print(f"[reranker] Cohere error: {e}")
        return chunks[:top_n]


def retrieve(query, use_hyde=True, use_hybrid=True, doc_type_filter=None):
    search_query = hyde_rewrite(query) if use_hyde else query

    if use_hybrid:
        vec   = vector_search(search_query, TOP_K, doc_type_filter)
        bm25  = bm25_search(query, TOP_K, doc_type_filter)
        fused = reciprocal_rank_fusion(vec, bm25)
    else:
        fused = vector_search(search_query, TOP_K, doc_type_filter)

    return rerank(query, fused, RERANK_TOP_N), search_query