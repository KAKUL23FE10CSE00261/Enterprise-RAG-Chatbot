"""
Run this once to create all project files.
python setup.py
"""
import os

# ── Create folders ────────────────────────────────────────────────────────────
for folder in ["app", "ingestion", "retrieval", "evaluation", "data\\sample_docs"]:
    os.makedirs(folder, exist_ok=True)
    print(f"Created folder: {folder}")

# ── Helper ────────────────────────────────────────────────────────────────────
def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written: {path}")

# ── __init__.py files ─────────────────────────────────────────────────────────
for p in ["app/__init__.py", "ingestion/__init__.py", "retrieval/__init__.py"]:
    write(p, "")

# ── ingestion/ingest.py ───────────────────────────────────────────────────────
write("ingestion/ingest.py", '''import os
from pathlib import Path
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz
from docx import Document

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "enterprise_docs"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
EMBED_MODEL = "text-embedding-3-small"

def load_pdf(path):
    doc = fitz.open(path)
    return "\\n".join(page.get_text() for page in doc)

def load_docx(path):
    doc = Document(path)
    return "\\n".join(p.text for p in doc.paragraphs if p.text.strip())

def load_txt(path):
    return Path(path).read_text(encoding="utf-8")

def load_document(path):
    ext = Path(path).suffix.lower()
    loaders = {".pdf": load_pdf, ".docx": load_docx, ".txt": load_txt}
    if ext not in loaders:
        raise ValueError(f"Unsupported file type: {ext}")
    return loaders[ext](path)

def chunk_text(text, source):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\\n\\n", "\\n", ".", " "],
    )
    chunks = splitter.split_text(text)
    return [{"text": c, "source": source, "chunk_id": i} for i, c in enumerate(chunks)]

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"], model_name=EMBED_MODEL)
    return client.get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=ef,
        metadata={"hnsw:space": "cosine"})

def ingest_file(file_path):
    print(f"Ingesting: {file_path}")
    text = load_document(file_path)
    chunks = chunk_text(text, source=file_path)
    collection = get_collection()
    collection.upsert(
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks],
        ids=[f"{Path(file_path).stem}_chunk_{c[\'chunk_id\']}" for c in chunks])
    print(f"  Stored {len(chunks)} chunks")

def ingest_folder(folder_path):
    folder = Path(folder_path)
    files = list(folder.glob("**/*.pdf")) + list(folder.glob("**/*.docx")) + list(folder.glob("**/*.txt"))
    for f in files:
        ingest_file(str(f))
    print(f"Done. Ingested {len(files)} files.")

if __name__ == "__main__":
    ingest_folder("data/sample_docs")
''')

# ── retrieval/retriever.py ────────────────────────────────────────────────────
write("retrieval/retriever.py", '''import os
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
''')

# ── app/rag_pipeline.py ───────────────────────────────────────────────────────
write("app/rag_pipeline.py", '''import os
from openai import OpenAI
from retrieval.retriever import retrieve

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """You are a helpful enterprise assistant. Answer using ONLY the provided context.
If the answer is not in the context, say: I dont have enough information in the uploaded documents.
Always cite source documents at the end: Sources: [filename]"""

def build_context(chunks):
    parts = []
    for i, chunk in enumerate(chunks):
        source = chunk["source"].replace("\\\\", "/").split("/")[-1]
        parts.append(f"[{i+1}] (Source: {source})\\n{chunk[\'text\']}")
    return "\\n\\n---\\n\\n".join(parts)

def extract_sources(chunks):
    seen, sources = set(), []
    for c in chunks:
        name = c["source"].replace("\\\\", "/").split("/")[-1]
        if name not in seen:
            seen.add(name)
            sources.append(name)
    return sources

def is_grounded(answer, chunks):
    context = build_context(chunks)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content":
            f"Context:\\n{context}\\n\\nAnswer:\\n{answer}\\n\\nIs every claim supported by the context? Reply YES or NO only."}],
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
    messages.append({"role": "user", "content": f"Context:\\n{context}\\n\\nQuestion: {query}"})
    resp = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.2, max_tokens=600)
    answer = resp.choices[0].message.content.strip()
    sources = extract_sources(chunks)
    grounded = is_grounded(answer, chunks) if check_grounding else True
    return {"answer": answer, "sources": sources, "grounded": grounded,
            "chunks_used": len(chunks), "rewritten_query": rewritten_query}
''')

# ── app/ui.py ─────────────────────────────────────────────────────────────────
write("app/ui.py", '''import os
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
''')

# ── evaluation/evaluate.py ────────────────────────────────────────────────────
write("evaluation/evaluate.py", '''import os
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.rag_pipeline import generate_answer
from retrieval.retriever import retrieve

TEST_CASES = [
    {"question": "What is the annual leave entitlement?",
     "ground_truth": "Full-time employees are entitled to 21 days of annual leave per year."},
    {"question": "What is the notice period for resignation?",
     "ground_truth": "Employees must give 30 days written notice before resigning."},
    {"question": "What is the work from home policy?",
     "ground_truth": "Employees may work from home up to 2 days per week with manager approval."},
    {"question": "How is overtime compensated?",
     "ground_truth": "Overtime is compensated at 1.5x the regular hourly rate."},
    {"question": "What is the probation period?",
     "ground_truth": "New employees serve a 3-month probation period."},
]

def run_evaluation():
    questions, answers, contexts, ground_truths = [], [], [], []
    for tc in TEST_CASES:
        q = tc["question"]
        print(f"Running: {q}")
        chunks, _ = retrieve(q, use_hyde=True)
        result = generate_answer(q, use_hyde=True, check_grounding=False)
        questions.append(q)
        answers.append(result["answer"])
        contexts.append([c["text"] for c in chunks])
        ground_truths.append(tc["ground_truth"])
    dataset = Dataset.from_dict({"question": questions, "answer": answers,
                                  "contexts": contexts, "ground_truth": ground_truths})
    llm = ChatOpenAI(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])
    emb = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.environ["OPENAI_API_KEY"])
    results = evaluate(dataset=dataset,
                       metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                       llm=llm, embeddings=emb)
    df = results.to_pandas()
    print("\\n===== RAGAS RESULTS =====")
    for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        print(f"  {m:<25} {df[m].mean():.3f}")
    df.to_json("evaluation/ragas_results.json", orient="records", indent=2)
    print("Saved to evaluation/ragas_results.json")

if __name__ == "__main__":
    run_evaluation()
''')

# ── data/sample_docs/hr_policy.txt ───────────────────────────────────────────
write("data/sample_docs/hr_policy.txt", """ACME CORP EMPLOYEE HANDBOOK

SECTION 1: ANNUAL LEAVE
Full-time employees are entitled to 21 days of annual leave per year.
Part-time employees receive leave on a pro-rata basis.
Leave must be approved by your manager at least 7 days in advance.
Unused leave of up to 10 days may be carried over to the next year.

SECTION 2: RESIGNATION & NOTICE PERIOD
Employees must give 30 days written notice before resigning.
Notice must be submitted in writing to HR and your direct manager.

SECTION 3: WORK FROM HOME POLICY
Employees may work from home up to 2 days per week with manager approval.
Core hours of 10am-4pm IST must be maintained regardless of work location.

SECTION 4: OVERTIME
Overtime is compensated at 1.5x the regular hourly rate for hours beyond 40 per week.
Overtime must be pre-approved by your manager in writing.

SECTION 5: PROBATION
New employees serve a 3-month probation period.
Benefits such as health insurance are active from Day 1.

SECTION 6: HEALTH INSURANCE
All employees and immediate family are covered under group health insurance.
Coverage limit: Rs. 5,00,000 per family per year.

SECTION 7: PERFORMANCE REVIEWS
Annual performance reviews are held in December.
Rating of 4 or above qualifies for a performance bonus.
""")

print("\n✅ All files created successfully!")
print("\nNext steps:")
print("  1. set OPENAI_API_KEY=sk-your-key-here")
print("  2. streamlit run app\\ui.py")