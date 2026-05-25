"""
app/rag_pipeline.py
Groq-powered RAG pipeline with:
  - Streaming generation (llama-3.3-70b-versatile)
  - Hallucination guard (llama-3.1-8b-instant)
  - Document summarizer
  - Follow-up question suggestions
"""

import os
from groq import Groq, APIError, RateLimitError, APITimeoutError, APIConnectionError
from retrieval.retriever import retrieve

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are a helpful, precise enterprise assistant.

Rules:
1. Answer using ONLY the provided context — never from prior knowledge.
2. If the answer is not found in context, say:
   "I don't have enough information in the uploaded documents."
3. Always end your response with: Sources: [filename(s)]
4. Be concise and structured. Use bullet points for lists."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_context(chunks):
    parts = []
    for i, c in enumerate(chunks):
        fn = c.get("filename") or c["source"].replace("\\","/").split("/")[-1]
        parts.append(f"[{i+1}] (Source: {fn})\n{c['text']}")
    return "\n\n---\n\n".join(parts)

def extract_sources(chunks):
    seen, out = set(), []
    for c in chunks:
        fn = c.get("filename") or c["source"].replace("\\","/").split("/")[-1]
        if fn not in seen:
            seen.add(fn); out.append(fn)
    return out

def is_grounded(answer, chunks):
    """Check if the answer is grounded in the provided context."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content":
                f"Context:\n{build_context(chunks)}\n\nAnswer:\n{answer}\n\n"
                "Is every factual claim in the Answer supported by the Context? Reply YES or NO only."}],
            max_tokens=5,
            timeout=10)
        return resp.choices[0].message.content.strip().upper().startswith("YES")
    except (APIError, RateLimitError, APITimeoutError, APIConnectionError):
        # Grounding check is best-effort; don't crash the main answer
        return True
    except Exception:
        return True


# ── Streaming answer ──────────────────────────────────────────────────────────

def stream_answer(query, history=None, use_hyde=True,
                  use_hybrid=True, doc_type_filter=None):
    """Yields text tokens then a final metadata dict."""
    try:
        chunks, rq = retrieve(query, use_hyde=use_hyde,
                              use_hybrid=use_hybrid, doc_type_filter=doc_type_filter)
    except Exception as e:
        yield f"⚠️ Retrieval error: {str(e)}. Please check your ChromaDB setup."
        yield {"sources": [], "grounded": False, "chunks_used": 0, "rewritten_query": query}
        return

    if not chunks:
        yield "No relevant documents found. Please upload and ingest documents first."
        yield {"sources": [], "grounded": False, "chunks_used": 0, "rewritten_query": rq}
        return

    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history: msgs.extend(history[-6:])
    msgs.append({"role": "user", "content": f"Context:\n{build_context(chunks)}\n\nQuestion: {query}"})

    full = ""
    try:
        for chunk in client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=msgs,
                temperature=0.2, max_tokens=700, stream=True, timeout=30):
            delta = chunk.choices[0].delta.content or ""
            full += delta
            yield delta
    except RateLimitError:
        yield "\n\n⚠️ Rate limit reached on Groq API. Please wait a moment and try again."
        yield {"sources": [], "grounded": False, "chunks_used": len(chunks), "rewritten_query": rq}
        return
    except APITimeoutError:
        yield "\n\n⚠️ Request timed out. The Groq API took too long to respond. Please retry."
        yield {"sources": [], "grounded": False, "chunks_used": len(chunks), "rewritten_query": rq}
        return
    except APIConnectionError:
        yield "\n\n⚠️ Could not connect to Groq API. Check your internet connection and API key."
        yield {"sources": [], "grounded": False, "chunks_used": len(chunks), "rewritten_query": rq}
        return
    except APIError as e:
        yield f"\n\n⚠️ Groq API error: {str(e)}. Please check your GROQ_API_KEY."
        yield {"sources": [], "grounded": False, "chunks_used": len(chunks), "rewritten_query": rq}
        return
    except Exception as e:
        yield f"\n\n⚠️ Unexpected error: {str(e)}"
        yield {"sources": [], "grounded": False, "chunks_used": len(chunks), "rewritten_query": rq}
        return

    srcs     = extract_sources(chunks)
    grounded = is_grounded(full, chunks)
    yield {"answer": full, "sources": srcs, "grounded": grounded,
           "chunks_used": len(chunks), "rewritten_query": rq}


# ── Non-streaming answer (used by evaluate.py) ────────────────────────────────

def generate_answer(query, history=None, use_hyde=True,
                    use_hybrid=True, doc_type_filter=None, check_grounding=True):
    """Non-streaming wrapper around stream_answer. Returns a dict with 'answer' key."""
    full_text = ""
    metadata  = {}
    for token in stream_answer(query, history=history, use_hyde=use_hyde,
                                use_hybrid=use_hybrid, doc_type_filter=doc_type_filter):
        if isinstance(token, dict):
            metadata = token
        else:
            full_text += token
    metadata["answer"] = full_text
    return metadata


# ── Document summarizer ───────────────────────────────────────────────────────

def summarize_document(filename, full_text):
    """Summarize an entire ingested document."""
    text = full_text[:6000] + ("..." if len(full_text) > 6000 else "")
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content":
                 "You are an expert document analyst. Provide a clear, structured summary."},
                {"role": "user", "content":
                 f"Summarize this document '{filename}' in the following format:\n\n"
                 "## 📋 Overview\n(2-3 sentence summary)\n\n"
                 "## 🔑 Key Points\n(5-7 bullet points)\n\n"
                 "## 💡 Main Conclusions\n(2-3 sentences)\n\n"
                 f"Document:\n{text}"}],
            temperature=0.3, max_tokens=800, timeout=30)
        return resp.choices[0].message.content.strip()
    except RateLimitError:
        return "⚠️ Rate limit reached. Please wait a moment and try summarising again."
    except (APITimeoutError, APIConnectionError):
        return "⚠️ Connection error. Please check your API key and internet connection."
    except APIError as e:
        return f"⚠️ API error while summarising: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"


# ── Follow-up question suggestions ───────────────────────────────────────────

def suggest_followups(query, answer, sources):
    """Generate 3 relevant follow-up questions based on the Q&A."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content":
                 "Generate exactly 3 short follow-up questions a user might ask next. "
                 "Return ONLY the 3 questions, one per line, no numbering, no extra text."},
                {"role": "user", "content":
                 f"User asked: {query}\n\nAssistant answered: {answer[:500]}\n\n"
                 "What are 3 natural follow-up questions?"}],
            temperature=0.7, max_tokens=150, timeout=15)
        lines = resp.choices[0].message.content.strip().split("\n")
        return [q.strip("- •123.").strip() for q in lines if q.strip()][:3]
    except (APIError, RateLimitError, APITimeoutError, APIConnectionError, Exception):
        return []
