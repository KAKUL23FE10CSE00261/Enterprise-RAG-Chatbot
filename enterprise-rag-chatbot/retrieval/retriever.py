import os
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "enterprise_docs"
EMBED_MODEL = "text-embedding-3-small"
TOP_K = 10
RERANK_TOP_N = 4

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"], model_name=EMBED_MODEL)
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)

def hyde_rewrite(query):
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Write a short factual paragraph answering this question:"},
            {"role": "user", "content": query}],
        max_tokens=200)
    return resp.choices[0].message.content.strip()

def vector_search(query, top_k=TOP_K):
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=top_k)
    return [{"text": doc, "source": meta.get("source", "unknown")}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])]

def rerank(query, chunks, top_n=RERANK_TOP_N):
    cohere_key = os.environ.get("COHERE_API_KEY")
    if cohere_key:
        import cohere
        co = cohere.Client(cohere_key)
        response = co.rerank(model="rerank-english-v3.0", query=query,
                             documents=[c["text"] for c in chunks], top_n=top_n)
        return [chunks[r.index] for r in response.results]
    return chunks[:top_n]

def retrieve(query, use_hyde=True):
    search_query = hyde_rewrite(query) if use_hyde else query
    chunks = vector_search(search_query, top_k=TOP_K)
    reranked = rerank(query, chunks, top_n=RERANK_TOP_N)
    return reranked, search_query
