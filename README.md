# 📄 Enterprise RAG Chatbot

> Upload PDFs, Word docs, or internal wikis — ask questions in natural language — get **cited, grounded answers** with zero hallucination from stale training data.

---

## ✨ Features 

| Feature | Detail |
|---|---|
| **Hybrid search** | Dense vector (ChromaDB) + BM25 keyword search fused with Reciprocal Rank Fusion |
| **HyDE rewriting** | Hypothetical Document Embeddings for better query-embedding alignment |
| **Cohere Reranker** | Cross-encoder reranking of top candidates for precision |
| **Hallucination guard** | Secondary LLM call verifies every claim is grounded in context |
| **Streaming responses** | Token-by-token output like ChatGPT |
| **Source citations** | Every answer cites the exact document(s) it came from |
| **Metadata filtering** | Filter retrieval by document type (HR, Legal, Research…) |
| **Feedback loop** | 👍 / 👎 ratings logged to JSONL for future fine-tuning |
| **RAGAS evaluation** | Automated faithfulness, relevancy, precision, recall scoring |
| **Docker ready** | One command to run anywhere |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│   Upload │ Chat │ Feedback │ Debug panel │ Settings     │
└────────────────────────┬────────────────────────────────┘
                         │ query
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  RAG Pipeline                           │
│                                                         │
│  1. HyDE rewrite (GPT-4o-mini)                         │
│     query → hypothetical answer paragraph               │
│                                                         │
│  2. Hybrid Retrieval                                    │
│     ├── Vector search  (ChromaDB / text-embedding-3)   │
│     └── BM25 keyword   (rank-bm25)                     │
│              ↓ Reciprocal Rank Fusion                   │
│                                                         │
│  3. Cohere Reranker  (top-5 from top-12)               │
│                                                         │
│  4. GPT-4o generation  (streaming, last-6-turn memory) │
│                                                         │
│  5. Hallucination guard (GPT-4o-mini grounding check)  │
└─────────────────────────────────────────────────────────┘
                         ▲
                         │ ingest
┌─────────────────────────────────────────────────────────┐
│                  Ingestion Pipeline                     │
│  PDF (PyMuPDF) / DOCX (python-docx) / TXT              │
│       ↓ RecursiveCharacterTextSplitter (512 / 50)      │
│       ↓ text-embedding-3-small                         │
│       ↓ ChromaDB upsert  + rich metadata               │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 RAGAS Evaluation Results

*(Run on ACME Corp HR Policy — sample document)*

| Metric | Score | What it means |
|---|---|---|
| **Faithfulness** | 0.94 | Answers grounded in retrieved context |
| **Answer Relevancy** | 0.91 | Answers actually address the question |
| **Context Precision** | 0.88 | Retrieved chunks are truly relevant |
| **Context Recall** | 0.86 | Retrieval captures all needed information |

> Run your own: `python -m evaluation.evaluate`

---

## 🚀 Quick Start

```bash
# 1 — Clone and install
git clone https://github.com/yourname/Enterprise-RAG-Chatbot.git
cd Enterprise-RAG-Chatbot
pip install -r requirements.txt

# 2 — Set API keys
set OPENAI_API_KEY=sk-...          # Windows
export OPENAI_API_KEY=sk-...       # Mac/Linux
# Optional: export COHERE_API_KEY=...

# 3 — Run
streamlit run app.py
```

**Or with Docker:**
```bash
docker build -t enterprise-rag .
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=sk-... \
  enterprise-rag
```

Then open http://localhost:8501

---

## 🗂️ Project Structure

```
enterprise-rag-chatbot/
├── app.py                        # Entry point: streamlit run app.py
├── requirements.txt
├── Dockerfile
├── app/
│   ├── ui.py                     # Streamlit UI (streaming, feedback, debug)
│   ├── rag_pipeline.py           # Generation + hallucination guard
│   └── feedback.py               # 👍/👎 logging + summary
├── ingestion/
│   └── ingest.py                 # Load → chunk → embed → ChromaDB
├── retrieval/
│   └── retriever.py              # HyDE + hybrid search + Cohere rerank
├── evaluation/
│   └── evaluate.py               # RAGAS eval script
├── data/
│   └── sample_docs/
│       └── hr_policy.txt
└── feedback/
    └── feedback.jsonl            # Auto-created on first thumbs click
```

---

## ⚙️ Tech Stack

| Layer | Tool |
|---|---|
| Frontend | Streamlit |
| LLM | GPT-4o (generation), GPT-4o-mini (HyDE + grounding) |
| Embeddings | text-embedding-3-small |
| Vector DB | ChromaDB (persistent) |
| Keyword search | rank-bm25 |
| Reranker | Cohere rerank-english-v3.0 |
| Document parsing | PyMuPDF, python-docx |
| Evaluation | RAGAS |
| Deployment | Docker |

---

## 🔮 Roadmap

- [ ] Pinecone swap-in for production scale
- [ ] JWT authentication
- [ ] Multi-modal RAG (tables + images via GPT-4V)
- [ ] HuggingFace Spaces deployment
- [ ] Fine-tuning pipeline from feedback JSONL 
