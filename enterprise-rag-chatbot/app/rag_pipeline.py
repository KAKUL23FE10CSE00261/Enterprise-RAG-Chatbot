"""
app/rag_pipeline.py
Core RAG pipeline: context building, streaming generation, hallucination guard.
"""

import os
from groq import Groq
from retrieval.retriever import retrieve

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

SYSTEM_PROMPT = """You are a helpful, precise enterprise assistant.

Rules:
1. Answer using ONLY the provided context — never from prior knowledge.
2. If the answer is not found in the context, say exactly:
   "I don't have enough information in the uploaded documents."
3. Always end your response with: Sources: [filename(s)]
4. Be concise and structured. Use bullet points for lists."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks):
        fn = chunk.get("filename") or chunk["source"].replace("\\", "/").split("/")[-1]
        parts.append(f"[{i+1}] (Source: {fn})\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def extract_sources(chunks: list[dict]) -> list[str]:
    seen, sources = set(), []
    for c in chunks:
        fn = c.get("filename") or c["source"].replace("\\", "/").split("/")[-1]
        if fn not in seen:
            seen.add(fn)
            sources.append(fn)
    return sources


def is_grounded(answer: str, chunks: list[dict]) -> bool:
    """Secondary LLM call: verify every claim in the answer is in the context."""
    context = build_context(chunks)
    resp = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{
            "role": "user",
            "content": (
                f"Context:\n{context}\n\n"
                f"Answer:\n{answer}\n\n"
                "Is every factual claim in the Answer supported by the Context? "
                "Reply YES or NO only."
            ),
        }],
        max_tokens=5,
    )
    return resp.choices[0].message.content.strip().upper().startswith("YES")


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_answer(
    query: str,
    history: list[dict] | None = None,
    use_hyde: bool = True,
    use_hybrid: bool = True,
    check_grounding: bool = True,
    doc_type_filter: str | None = None,
) -> dict:
    """
    Non-streaming generation. Returns a result dict.
    """
    chunks, rewritten_query = retrieve(
        query,
        use_hyde=use_hyde,
        use_hybrid=use_hybrid,
        doc_type_filter=doc_type_filter,
    )

    if not chunks:
        return {
            "answer":          "No relevant documents found. Please upload documents first.",
            "sources":         [],
            "grounded":        False,
            "chunks_used":     0,
            "rewritten_query": rewritten_query,
        }

    context  = build_context(chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])
    messages.append({
        "role":    "user",
        "content": f"Context:\n{context}\n\nQuestion: {query}",
    })

    resp   = client.chat.completions.create(
        model="gpt-4o", messages=messages, temperature=0.2, max_tokens=700
    )
    answer  = resp.choices[0].message.content.strip()
    sources = extract_sources(chunks)
    grounded = is_grounded(answer, chunks) if check_grounding else True

    return {
        "answer":          answer,
        "sources":         sources,
        "grounded":        grounded,
        "chunks_used":     len(chunks),
        "rewritten_query": rewritten_query,
    }


def stream_answer(
    query: str,
    history: list[dict] | None = None,
    use_hyde: bool = True,
    use_hybrid: bool = True,
    doc_type_filter: str | None = None,
):
    """
    Streaming generator. Yields text tokens, then a final metadata dict.
    Usage:
        for token in stream_answer(query):
            if isinstance(token, dict):   # final metadata
                sources = token["sources"]
            else:
                print(token, end="")
    """
    chunks, rewritten_query = retrieve(
        query,
        use_hyde=use_hyde,
        use_hybrid=use_hybrid,
        doc_type_filter=doc_type_filter,
    )

    if not chunks:
        yield "No relevant documents found. Please upload documents first."
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
        model="gpt-4o", messages=messages,
        temperature=0.2, max_tokens=700, stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        full_answer += delta
        yield delta

    # After streaming finishes, emit metadata
    sources  = extract_sources(chunks)
    grounded = is_grounded(full_answer, chunks)
    yield {
        "answer":          full_answer,
        "sources":         sources,
        "grounded":        grounded,
        "chunks_used":     len(chunks),
        "rewritten_query": rewritten_query,
    }
