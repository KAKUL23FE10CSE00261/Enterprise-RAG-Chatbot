"""
Retrieval module.
Handles query rewriting (HyDE), vector search, and Cohere reranking.
"""

import os
from typing import List, Tuple
from openai import OpenAI
import cohere
import chromadb
from chromadb.utils import embedding_functions

from ingestion.ingest import CHROMA_PATH, COLLECTION_NAME, EMBED_MODEL


openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
cohere_client = cohere.Client(os.environ.get("COHERE_API_KEY", ""))

TOP_K = 10          # chunks fetched from vector DB
RERANK_TOP_N = 4    # chunks sent to LLM after reranking


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=EMBED_MODEL,
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=openai_ef,
    )


# ── Query rewriting via HyDE ─────────────────────────────────────────────────

def hyde_rewrite(query: str) -> str:
    """
    HyDE: generate a hypothetical answer, then embed THAT for retrieval.
    This dramatically improves recall for vague or short queries.
    """
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Write a short, factual paragraph that would answer the following question. Be concise."},
            {"role": "user", "content": query},
        ],
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


# ── Vector retrieval ──────────────────────────────────────────────────────────

def vector_search(query: str, top_k: int = TOP_K) -> List[dict]:
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=top_k)
    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"text": doc, "source": meta.get("source", "unknown")})
    return chunks


# ── Cohere reranker ───────────────────────────────────────────────────────────

def rerank(query: str, chunks: List[dict], top_n: int = RERANK_TOP_N) -> List[dict]:
    if not os.environ.get("COHERE_API_KEY"):
        return chunks[:top_n]  # fallback: just take top-k without reranking

    response = cohere_client.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=[c["text"] for c in chunks],
        top_n=top_n,
    )
    reranked = []
    for r in response.results:
        chunk = chunks[r.index].copy()
        chunk["relevance_score"] = round(r.relevance_score, 4)
        reranked.append(chunk)
    return reranked


# ── Main retrieve function ────────────────────────────────────────────────────

def retrieve(query: str, use_hyde: bool = True) -> Tuple[List[dict], str]:
    """
    Full retrieval pipeline:
      1. Optionally rewrite query with HyDE
      2. Vector search top-k chunks
      3. Rerank → return top-n chunks + the rewritten query
    """
    search_query = hyde_rewrite(query) if use_hyde else query
    chunks = vector_search(search_query, top_k=TOP_K)
    reranked = rerank(query, chunks, top_n=RERANK_TOP_N)
    return reranked, search_query


if __name__ == "__main__":
    chunks, rewritten = retrieve("What is the leave policy?")
    print(f"Rewritten query: {rewritten}\n")
    for i, c in enumerate(chunks):
        print(f"[{i+1}] Score: {c.get('relevance_score', '-')} | Source: {c['source']}")
        print(f"     {c['text'][:120]}...\n")