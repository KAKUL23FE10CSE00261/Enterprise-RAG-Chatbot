"""
app/ui.py  —  Enterprise RAG Chatbot  (Streamlit)

Features:
  • Streaming responses (token-by-token)
  • Hybrid search toggle (vector + BM25)
  • HyDE query rewriting toggle
  • Hallucination guard toggle
  • Document-type metadata filter
  • Thumbs-up / thumbs-down feedback with comment
  • Debug panel (rewritten query, chunks used, grounding)
  • Ingested files list in sidebar
"""

import os
import tempfile
from pathlib import Path

import streamlit as st

# ── API key check (must come before any other imports that need it) ─────────────
if not os.environ.get("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY not set. Run:  set OPENAI_API_KEY=sk-...")
    st.stop()

from ingestion.ingest import ingest_file, list_ingested_files
from app.rag_pipeline import stream_answer
from app.feedback import log_feedback, feedback_summary

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise RAG Chatbot",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .source-badge {
    background: #1e3a5f; color: #a8d4ff;
    border-radius: 4px; padding: 2px 8px;
    font-size: 0.78rem; margin-right: 4px;
  }
  .warning-box {
    background: #3d2600; border-left: 3px solid #ff9900;
    padding: 8px 12px; border-radius: 4px; font-size: 0.85rem;
  }
  .feedback-row { display: flex; gap: 8px; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)

st.title("📄 Enterprise RAG Chatbot")
st.caption("Upload documents · Ask questions · Get cited, grounded answers")

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("messages", []),
    ("history",  []),
    ("pending_feedback_idx", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📁 Documents")

    uploaded_files = st.file_uploader(
        "Upload PDF, DOCX, or TXT",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )

    doc_type = st.selectbox(
        "Document type (for filtering)",
        ["general", "hr", "legal", "research", "finance", "technical"],
    )

    if uploaded_files:
        if st.button("⚡ Ingest documents", type="primary", use_container_width=True):
            progress = st.progress(0, text="Starting…")
            for i, uf in enumerate(uploaded_files):
                progress.progress((i + 1) / len(uploaded_files), text=f"Processing {uf.name}…")
                suffix = Path(uf.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uf.read())
                    tmp_path = tmp.name
                ingest_file(tmp_path, doc_type=doc_type)
                os.unlink(tmp_path)
            progress.empty()
            st.success(f"✓ Ingested {len(uploaded_files)} file(s) as [{doc_type}]")
            st.rerun()

    # Ingested files list
    ingested = list_ingested_files()
    if ingested:
        with st.expander(f"📂 Ingested files ({len(ingested)})", expanded=False):
            for fn in ingested:
                st.text(f"• {fn}")
    else:
        st.info("No documents ingested yet.")

    st.divider()
    st.header("⚙️ Settings")

    use_hybrid      = st.toggle("Hybrid search (vector + BM25)", value=True,
                                help="Combines dense and keyword search for better recall")
    use_hyde        = st.toggle("HyDE query rewriting",          value=True,
                                help="Generates a hypothetical answer to improve embedding alignment")
    check_grounding = st.toggle("Hallucination guard",           value=True,
                                help="Secondary LLM call verifies every claim is grounded")
    show_debug      = st.toggle("Debug panel",                   value=False)

    doc_filter = st.selectbox(
        "Filter by doc type (optional)",
        ["All"] + ["general", "hr", "legal", "research", "finance", "technical"],
    )
    active_filter = None if doc_filter == "All" else doc_filter

    st.divider()
    st.header("📊 Feedback stats")
    fs = feedback_summary()
    c1, c2 = st.columns(2)
    c1.metric("👍 Thumbs up",   fs["thumbs_up"])
    c2.metric("👎 Thumbs down", fs["thumbs_down"])
    if fs["total"]:
        st.progress(fs["approval_rate"] / 100, text=f"{fs['approval_rate']}% approval")

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history  = []
        st.rerun()

# ── Chat display ──────────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            # Source badges
            if msg.get("sources"):
                badges = "".join(
                    f'<span class="source-badge">📎 {s}</span>'
                    for s in msg["sources"]
                )
                st.markdown(badges, unsafe_allow_html=True)

            # Hallucination warning
            if msg.get("warning"):
                st.markdown(
                    f'<div class="warning-box">⚠️ {msg["warning"]}</div>',
                    unsafe_allow_html=True,
                )

            # Debug panel
            if show_debug and msg.get("debug"):
                with st.expander("🔍 Debug"):
                    st.json(msg["debug"])

            # Feedback buttons (only for messages not yet rated)
            if not msg.get("rated"):
                col1, col2, _ = st.columns([1, 1, 8])
                if col1.button("👍", key=f"up_{idx}"):
                    log_feedback(
                        query=msg.get("query", ""),
                        answer=msg["content"],
                        sources=msg.get("sources", []),
                        rating="up",
                    )
                    st.session_state.messages[idx]["rated"] = True
                    st.rerun()
                if col2.button("👎", key=f"down_{idx}"):
                    log_feedback(
                        query=msg.get("query", ""),
                        answer=msg["content"],
                        sources=msg.get("sources", []),
                        rating="down",
                    )
                    st.session_state.messages[idx]["rated"] = True
                    st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────
query = st.chat_input("Ask a question about your documents…")

if query:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Stream assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text   = ""
        metadata    = {}

        for token in stream_answer(
            query=query,
            history=st.session_state.history,
            use_hyde=use_hyde,
            use_hybrid=use_hybrid,
            doc_type_filter=active_filter,
        ):
            if isinstance(token, dict):
                metadata = token
            else:
                full_text += token
                placeholder.markdown(full_text + "▌")

        placeholder.markdown(full_text)

        sources  = metadata.get("sources", [])
        grounded = metadata.get("grounded", True)
        warning  = None

        if sources:
            badges = "".join(
                f'<span class="source-badge">📎 {s}</span>' for s in sources
            )
            st.markdown(badges, unsafe_allow_html=True)

        if not grounded:
            warning = "Answer may not be fully supported by the uploaded documents."
            st.markdown(
                f'<div class="warning-box">⚠️ {warning}</div>',
                unsafe_allow_html=True,
            )

        if show_debug:
            with st.expander("🔍 Debug"):
                st.json({
                    "rewritten_query": metadata.get("rewritten_query"),
                    "chunks_used":     metadata.get("chunks_used"),
                    "grounded":        grounded,
                    "hybrid_search":   use_hybrid,
                    "hyde":            use_hyde,
                    "doc_filter":      active_filter,
                })

    # Save to session state
    st.session_state.messages.append({
        "role":    "assistant",
        "content": full_text,
        "sources": sources,
        "warning": warning,
        "query":   query,
        "rated":   False,
        "debug": {
            "rewritten_query": metadata.get("rewritten_query"),
            "chunks_used":     metadata.get("chunks_used"),
            "grounded":        grounded,
        },
    })

    # Update conversation history for multi-turn context
    st.session_state.history.extend([
        {"role": "user",      "content": query},
        {"role": "assistant", "content": full_text},
    ])
