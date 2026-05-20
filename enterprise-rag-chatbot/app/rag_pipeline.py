"""
app/rag_pipeline.py
Uses Groq API (free, fast) with llama3-70b for generation.
Embeddings use local SentenceTransformer — no OpenAI key needed.
"""

import os
from groq import Groq
from retrieval.retriever import retrieve

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are a helpful, precise enterprise assistant.

Rules:
1. Answer using ONLY the provided context — never from prior knowledge.
2. If the answer is not found in the context, say exactly:
   "I don't have enough information in the uploaded documents."
3. Always end your response with: Sources: [filename(s)]
4. Be concise and structured. Use bullet points for lists."""


def build_context(chunks):
    parts = []
    for i, chunk in enumerate(chunks):
        fn = chunk.get("filename") or chunk["source"].replace("\\", "/").split("/")[-1]
        parts.append(f"[{i+1}] (Source: {fn})\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def extract_sources(chunks):
    seen, sources = set(), []
    for c in chunks:
        fn = c.get("filename") or c["source"].replace("\\", "/").split("/")[-1]
        if fn not in seen:
            seen.add(fn)
            sources.append(fn)
    return sources


def is_grounded(answer, chunks):
    context = build_context(chunks)
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content":
            f"Context:\n{context}\n\nAnswer:\n{answer}\n\n"
            "Is every factual claim in the Answer supported by the Context? "
            "Reply YES or NO only."}],
        max_tokens=5,
    )
    return resp.choices[0].message.content.strip().upper().startswith("YES")


def stream_answer(
    query,
    history=None,
    use_hyde=True,
    use_hybrid=True,
    doc_type_filter=None,
):
    """Streaming generator. Yields text tokens, then a final metadata dict."""
    chunks, rewritten_query = retrieve(
        query,
        use_hyde=use_hyde,
        use_hybrid=use_hybrid,
        doc_type_filter=doc_type_filter,
    )

    if not chunks:
        yield "No relevant documents found. Please upload and ingest documents first."
        yield {"sources": [], "grounded": False,
               "chunks_used": 0, "rewritten_query": rewritten_query}
        return

    context  = build_context(chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])
    messages.append({
        "role":    "user",
        "content": f"Context:\n{context}\n\nQuestion: {query}",
    })

    full_answer = ""
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.2,
        max_tokens=700,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        full_answer += delta
        yield delta

    sources  = extract_sources(chunks)
    grounded = is_grounded(full_answer, chunks)
    yield {
        "answer":          full_answer,
        "sources":         sources,
        "grounded":        grounded,
        "chunks_used":     len(chunks),
        "rewritten_query": rewritten_query,
    }