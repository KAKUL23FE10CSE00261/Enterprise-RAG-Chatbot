import os
import streamlit as st
import tempfile
from pathlib import Path

if not os.environ.get("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY not set. In terminal run: set OPENAI_API_KEY=sk-...")
    st.stop()

from ingestion.ingest import ingest_file
from app.rag_pipeline import generate_answer

st.set_page_config(page_title="Enterprise RAG Chatbot", page_icon="📄", layout="wide")
st.title("📄 Enterprise RAG Chatbot")
st.caption("Upload documents and ask questions — grounded answers with citations.")

with st.sidebar:
    st.header("Upload documents")
    uploaded_files = st.file_uploader("PDF, DOCX, or TXT", type=["pdf","docx","txt"], accept_multiple_files=True)
    if uploaded_files:
        if st.button("Ingest documents", type="primary"):
            progress = st.progress(0, text="Starting...")
            for i, uf in enumerate(uploaded_files):
                progress.progress((i+1)/len(uploaded_files), text=f"Processing {uf.name}...")
                suffix = Path(uf.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uf.read())
                    tmp_path = tmp.name
                ingest_file(tmp_path)
                os.unlink(tmp_path)
            progress.empty()
            st.success(f"Ingested {len(uploaded_files)} file(s)!")
    st.divider()
    use_hyde = st.toggle("HyDE query rewriting", value=True)
    check_grounding = st.toggle("Hallucination guard", value=True)
    show_debug = st.toggle("Show debug info", value=False)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption("Sources: " + " · ".join(f"`{s}`" for s in msg["sources"]))
        if msg.get("warning"):
            st.warning(msg["warning"])

query = st.chat_input("Ask a question about your documents...")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Searching and generating answer..."):
            result = generate_answer(query=query, history=st.session_state.history,
                                     use_hyde=use_hyde, check_grounding=check_grounding)
        answer = result["answer"]
        sources = result["sources"]
        grounded = result["grounded"]
        st.markdown(answer)
        if sources:
            st.caption("Sources: " + " · ".join(f"`{s}`" for s in sources))
        warning = None
        if not grounded:
            warning = "Hallucination guard: answer may not be fully supported by documents."
            st.warning(warning)
        if show_debug:
            with st.expander("Debug"):
                st.json({"rewritten_query": result["rewritten_query"],
                         "chunks_used": result["chunks_used"], "grounded": grounded})
    st.session_state.messages.append({"role": "assistant", "content": answer,
                                       "sources": sources, "warning": warning})
    st.session_state.history.extend([{"role": "user", "content": query},
                                      {"role": "assistant", "content": answer}])
