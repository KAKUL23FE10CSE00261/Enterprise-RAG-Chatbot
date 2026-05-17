import os
from openai import OpenAI
from retrieval.retriever import retrieve

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """You are a helpful enterprise assistant. Answer using ONLY the provided context.
If the answer is not in the context, say: I dont have enough information in the uploaded documents.
Always cite source documents at the end: Sources: [filename]"""

def build_context(chunks):
    parts = []
    for i, chunk in enumerate(chunks):
        source = chunk["source"].replace("\\", "/").split("/")[-1]
        parts.append(f"[{i+1}] (Source: {source})\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)

def extract_sources(chunks):
    seen, sources = set(), []
    for c in chunks:
        name = c["source"].replace("\\", "/").split("/")[-1]
        if name not in seen:
            seen.add(name)
            sources.append(name)
    return sources

def is_grounded(answer, chunks):
    context = build_context(chunks)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content":
            f"Context:\n{context}\n\nAnswer:\n{answer}\n\nIs every claim supported by the context? Reply YES or NO only."}],
        max_tokens=5)
    return resp.choices[0].message.content.strip().upper().startswith("YES")

def generate_answer(query, history=None, use_hyde=True, check_grounding=True):
    chunks, rewritten_query = retrieve(query, use_hyde=use_hyde)
    if not chunks:
        return {"answer": "No relevant documents found. Please upload documents first.",
                "sources": [], "grounded": False, "chunks_used": 0, "rewritten_query": rewritten_query}
    context = build_context(chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"})
    resp = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.2, max_tokens=600)
    answer = resp.choices[0].message.content.strip()
    sources = extract_sources(chunks)
    grounded = is_grounded(answer, chunks) if check_grounding else True
    return {"answer": answer, "sources": sources, "grounded": grounded,
            "chunks_used": len(chunks), "rewritten_query": rewritten_query}
