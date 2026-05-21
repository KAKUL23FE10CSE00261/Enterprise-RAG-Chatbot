"""
app/ui.py — Enterprise RAG Chatbot
Features:
  ✅ Real filename in sources (no more tmp names)
  ✅ Chat history export (TXT + HTML)
  ✅ Document summarizer
  ✅ Follow-up question suggestions
  ✅ Streaming responses
  ✅ Hybrid search + HyDE + hallucination guard
  ✅ Feedback stats
"""

import os, sys, tempfile, json
from pathlib import Path
from datetime import datetime
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── API key check ─────────────────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    st.error("**GROQ_API_KEY not set.**\n\nIn terminal:\n```\nset GROQ_API_KEY=gsk_your-key\n```")
    st.stop()

from ingestion.ingest import ingest_file, list_ingested_files, get_full_text
from app.rag_pipeline import stream_answer, summarize_document, suggest_followups
from app.feedback import log_feedback, feedback_summary

st.set_page_config(page_title="Enterprise RAG Chatbot", page_icon="📄",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  .source-badge {
    background:#1e3a5f; color:#a8d4ff;
    border-radius:4px; padding:2px 8px;
    font-size:0.78rem; margin-right:4px; display:inline-block;
  }
  .warning-box {
    background:#3d2600; border-left:3px solid #ff9900;
    padding:8px 12px; border-radius:4px; font-size:0.85rem;
  }
  .followup-btn { margin: 2px 0; }
</style>
""", unsafe_allow_html=True)

st.title("📄 Enterprise RAG Chatbot")
st.caption("Upload documents · Ask questions · Get cited, grounded answers  |  Powered by Groq + Llama 3")

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("messages",[]), ("history",[]), ("model_ready",False),
             ("pending_query", None), ("show_summary", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Pre-warm embedding model ──────────────────────────────────────────────────
if not st.session_state.model_ready:
    with st.spinner("⏳ Loading embedding model (first time only ~30s)…"):
        try:
            from ingestion.ingest import get_collection
            get_collection()
        except Exception:
            pass
        st.session_state.model_ready = True

# ── Chat export helpers ───────────────────────────────────────────────────────
def export_txt():
    lines = [f"Enterprise RAG Chatbot — Export {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
             "="*60 + "\n"]
    for m in st.session_state.messages:
        role = "You" if m["role"] == "user" else "Assistant"
        lines.append(f"\n[{role}]\n{m['content']}")
        if m.get("sources"):
            lines.append(f"Sources: {', '.join(m['sources'])}")
        lines.append("")
    return "\n".join(lines)

def export_html():
    rows = ""
    for m in st.session_state.messages:
        role  = m["role"]
        color = "#1e3a5f" if role == "assistant" else "#2d2d2d"
        label = "🤖 Assistant" if role == "assistant" else "👤 You"
        srcs  = ""
        if m.get("sources"):
            srcs = "<br><small>📎 " + " · ".join(m["sources"]) + "</small>"
        rows += f"""<div style="margin:12px 0;padding:12px;background:{color};border-radius:8px">
            <b>{label}</b><br>{m['content']}{srcs}</div>"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>RAG Chat Export</title>
    <style>body{{font-family:sans-serif;max-width:860px;margin:auto;padding:20px;background:#111;color:#eee}}</style>
    </head><body><h2>📄 Enterprise RAG Chatbot Export</h2>
    <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>{rows}</body></html>"""


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Documents ──────────────────────────────────────────────────────────────
    st.header("📁 Documents")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, or TXT",
                                       type=["pdf","docx","txt"],
                                       accept_multiple_files=True)
    doc_type = st.selectbox("Document type",
                             ["general","hr","legal","research","finance","technical"])

    if uploaded_files:
        if st.button("⚡ Ingest documents", type="primary", use_container_width=True):
            bar    = st.progress(0)
            status = st.empty()
            for i, uf in enumerate(uploaded_files):
                bar.progress((i+1)/len(uploaded_files), text=f"Processing {uf.name}…")
                status.info(f"Embedding {uf.name}…")
                sfx = Path(uf.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=sfx) as tmp:
                    tmp.write(uf.read()); path = tmp.name
                try:
                    n = ingest_file(path, doc_type=doc_type,
                                    original_filename=uf.name)   # ← real filename fix
                    status.success(f"✅ {uf.name} — {n} chunks")
                except Exception as e:
                    status.error(f"❌ {uf.name}: {e}")
                finally:
                    os.unlink(path)
            bar.empty()
            st.success(f"Ingested {len(uploaded_files)} file(s)!")
            st.rerun()

    ingested = list_ingested_files()
    if ingested:
        with st.expander(f"📂 Ingested files ({len(ingested)})", expanded=False):
            for fn in ingested:
                st.text(f"• {fn}")
    else:
        st.info("No documents ingested yet.")

    # ── Document summarizer ────────────────────────────────────────────────────
    st.divider()
    st.header("📝 Summarize Document")
    if ingested:
        sel_file = st.selectbox("Choose document", ingested, key="sum_sel")
        if st.button("Generate summary", use_container_width=True):
            with st.spinner(f"Summarizing {sel_file}…"):
                full_text = get_full_text(sel_file)
                if full_text:
                    summary = summarize_document(sel_file, full_text)
                    st.session_state.show_summary = {"file": sel_file, "text": summary}
                else:
                    st.warning("Could not retrieve text for this file.")
    else:
        st.info("Ingest a document first.")

    # ── Settings ───────────────────────────────────────────────────────────────
    st.divider()
    st.header("⚙️ Settings")
    use_hybrid      = st.toggle("Hybrid search (vector + BM25)", value=True)
    use_hyde        = st.toggle("HyDE query rewriting",          value=True)
    check_grounding = st.toggle("Hallucination guard",           value=True)
    show_debug      = st.toggle("Debug panel",                   value=False)
    doc_filter      = st.selectbox("Filter by doc type",
                                    ["All","general","hr","legal","research","finance","technical"])
    active_filter   = None if doc_filter == "All" else doc_filter

    # ── Export chat ────────────────────────────────────────────────────────────
    st.divider()
    st.header("💾 Export Chat")
    if st.session_state.messages:
        col1, col2 = st.columns(2)
        col1.download_button(
            "📄 TXT", data=export_txt(),
            file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain", use_container_width=True)
        col2.download_button(
            "🌐 HTML", data=export_html(),
            file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html", use_container_width=True)
    else:
        st.caption("No chat to export yet.")

    # ── Feedback stats ─────────────────────────────────────────────────────────
    st.divider()
    st.header("📊 Feedback stats")
    fs = feedback_summary()
    c1, c2 = st.columns(2)
    c1.metric("👍", fs["thumbs_up"])
    c2.metric("👎", fs["thumbs_down"])
    if fs["total"]:
        st.progress(fs["approval_rate"]/100, text=f"{fs['approval_rate']}% approval")

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history  = []
        st.session_state.show_summary = None
        st.rerun()


# ── Summary panel (shows above chat) ─────────────────────────────────────────
if st.session_state.show_summary:
    s = st.session_state.show_summary
    with st.expander(f"📋 Summary: {s['file']}", expanded=True):
        st.markdown(s["text"])
        if st.button("✕ Close summary"):
            st.session_state.show_summary = None
            st.rerun()

# ── Chat display ──────────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            if msg.get("sources"):
                badges = "".join(f'<span class="source-badge">📎 {s}</span>'
                                 for s in msg["sources"])
                st.markdown(badges, unsafe_allow_html=True)

            if msg.get("warning"):
                st.markdown(f'<div class="warning-box">⚠️ {msg["warning"]}</div>',
                            unsafe_allow_html=True)

            if show_debug and msg.get("debug"):
                with st.expander("🔍 Debug"):
                    st.json(msg["debug"])

            # Follow-up suggestions
            if msg.get("followups"):
                st.markdown("**💡 Follow-up questions:**")
                for fq in msg["followups"]:
                    if st.button(f"→ {fq}", key=f"fq_{idx}_{fq[:20]}",
                                 use_container_width=False):
                        st.session_state.pending_query = fq
                        st.rerun()

            # Feedback
            if not msg.get("rated"):
                col1, col2, _ = st.columns([1, 1, 8])
                if col1.button("👍", key=f"up_{idx}"):
                    log_feedback(query=msg.get("query",""), answer=msg["content"],
                                 sources=msg.get("sources",[]), rating="up")
                    st.session_state.messages[idx]["rated"] = True
                    st.rerun()
                if col2.button("👎", key=f"down_{idx}"):
                    log_feedback(query=msg.get("query",""), answer=msg["content"],
                                 sources=msg.get("sources",[]), rating="down")
                    st.session_state.messages[idx]["rated"] = True
                    st.rerun()


# ── Chat input ────────────────────────────────────────────────────────────────
# Handle follow-up button clicks OR direct chat input
query = st.chat_input("Ask a question about your documents…")
if st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = None

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text   = ""
        metadata    = {}

        for token in stream_answer(query=query, history=st.session_state.history,
                                   use_hyde=use_hyde, use_hybrid=use_hybrid,
                                   doc_type_filter=active_filter):
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
            badges = "".join(f'<span class="source-badge">📎 {s}</span>' for s in sources)
            st.markdown(badges, unsafe_allow_html=True)

        if not grounded:
            warning = "Answer may not be fully supported by the uploaded documents."
            st.markdown(f'<div class="warning-box">⚠️ {warning}</div>', unsafe_allow_html=True)

        # Generate follow-up suggestions
        followups = []
        try:
            with st.spinner("Generating follow-up suggestions…"):
                followups = suggest_followups(query, full_text, sources)
            if followups:
                st.markdown("**💡 Follow-up questions:**")
                for fq in followups:
                    if st.button(f"→ {fq}", key=f"new_fq_{fq[:20]}",
                                 use_container_width=False):
                        st.session_state.pending_query = fq
                        st.rerun()
        except Exception:
            pass

        if show_debug:
            with st.expander("🔍 Debug"):
                st.json({"rewritten_query": metadata.get("rewritten_query"),
                         "chunks_used": metadata.get("chunks_used"),
                         "grounded": grounded})

    st.session_state.messages.append({
        "role": "assistant", "content": full_text,
        "sources": sources, "warning": warning,
        "query": query, "rated": False, "followups": followups,
        "debug": {"rewritten_query": metadata.get("rewritten_query"),
                  "chunks_used": metadata.get("chunks_used"), "grounded": grounded},
    })
    st.session_state.history.extend([
        {"role": "user",      "content": query},
        {"role": "assistant", "content": full_text},
    ])