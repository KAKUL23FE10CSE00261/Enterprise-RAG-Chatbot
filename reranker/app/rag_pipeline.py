"""
RAG generation pipeline.
Builds prompt from retrieved chunks, calls LLM, verifies grounding,
and returns answer + source citations.
"""

import os
from typing import List, Tuple
from openai import OpenAI

from retrieval.retriever import retrieve

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """You are a helpful enterprise assistant. Answer the user's question
using ONLY the provided context. If the answer is not in the context, say:
"I don't have enough information in the uploaded documents to answer this."

Always cite the source document(s) at the end of your answer in this format:
Sources: [filename1, filename2]

Be concise, factual, and professional."""


def build_context(chunks: List[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks):
        source = chunk["source"].split("/")[-1]  # just filename
        parts.append(f"[{i+1}] (Source: {source})\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def is_grounded(answer: str, chunks: List[dict]) -> bool:
    """
    Simple hallucination guard:
    Ask GPT-4o-mini whether the answer is supported by the context.
    """
    context = build_context(chunks)
    check_prompt = f"""Context:
{context}

Answer:
{answer}

Is every factual claim in the answer directly supported by the context above?
Reply with only YES or NO."""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": check_prompt}],
        max_tokens=5,
    )
    verdict = resp.choices[0].message.content.strip().upper()
    return verdict.startswith("YES")


def extract_sources(chunks: List[dict]) -> List[str]:
    seen = set()
    sources = []
    for c in chunks:
        name = c["source"].split("/")[-1]
        if name not in seen:
            seen.add(name)
            sources.append(name)
    return sources


def generate_answer(
    query: str,
    history: List[dict] = None,
    use_hyde: bool = True,
    check_grounding: bool = True,
) -> dict:
    """
    Full RAG answer generation.

    Returns:
        {
          "answer": str,
          "sources": List[str],
          "grounded": bool,
          "chunks_used": int,
          "rewritten_query": str,
        }
    """
    chunks, rewritten_query = retrieve(query, use_hyde=use_hyde)

    if not chunks:
        return {
            "answer": "No relevant documents found. Please upload documents first.",
            "sources": [],
            "grounded": False,
            "chunks_used": 0,
            "rewritten_query": rewritten_query,
        }

    context = build_context(chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history[-6:])  # last 3 turns for memory

    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {query}",
    })

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2,
        max_tokens=600,
        stream=False,
    )

    answer = resp.choices[0].message.content.strip()
    sources = extract_sources(chunks)
    grounded = is_grounded(answer, chunks) if check_grounding else True

    return {
        "answer": answer,
        "sources": sources,
        "grounded": grounded,
        "chunks_used": len(chunks),
        "rewritten_query": rewritten_query,
    }


if __name__ == "__main__":
    result = generate_answer("What is the annual leave entitlement?")
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])
    print("Grounded:", result["grounded"])