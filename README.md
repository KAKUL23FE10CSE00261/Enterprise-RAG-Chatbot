# StudyMind AI — Enterprise RAG Chatbot

An advanced Retrieval-Augmented Generation (RAG) chatbot built for students and enterprises. Upload PDFs, DOCX, and TXT documents, ask questions in natural language, and receive streaming, source-grounded answers powered by a hybrid retrieval pipeline.

Includes a PYQ (Previous Year Question) analyzer, AI study planner, RAGAS evaluation dashboard, per-user session persistence, and hallucination detection.

---

## Features

### Document Chat
- Upload PDF, DOCX, and TXT files — ingest multiple files at once
- Tag each document by type: `syllabus`, `timetable`, `fees`, `rules`, `pyq`, or `general`
- Filter retrieval by document type per query
- Streaming token-by-token responses (like ChatGPT)
- Source citations on every answer (`📄 filename`)
- Hallucination guard — a secondary LLM call verifies every answer against retrieved context and flags ungrounded claims

### Hybrid Retrieval Pipeline
- **HyDE rewriting** — generates a hypothetical answer to the query, then embeds that instead of the raw question for better semantic alignment
- **Dense vector search** — ChromaDB with `all-MiniLM-L6-v2` embeddings (cosine similarity), TOP_K = 12
- **BM25 keyword search** — exact-match search across all stored chunks via `rank-bm25`
- **Reciprocal Rank Fusion (RRF)** — fuses vector and BM25 results without needing to tune weights
- **Cohere reranking** — cross-encoder reranking with `rerank-english-v3.0`, returns top 5 chunks (optional, requires `COHERE_API_KEY`)

### PYQ Analyzer
- Upload 1–3 years of previous year question PDFs
- Topic frequency extraction and bar chart visualisation
- Exam difficulty assessment
- Top 5 predicted topics for the next exam
- Multi-year comparison — identifies topics that appear every year vs. topics due to appear

### Study Planner
- Single-subject day-by-day schedule: enter subject, exam date, and hours per day
- Multi-subject combined weekly timetable with priority weighting
- Schedule is generated from syllabus chunks retrieved from ChromaDB (upload your syllabus PDF first)

### Evaluation — RAGAS Dashboard
- Run RAGAS evaluation against a 7-question HR policy test suite
- Metrics: **Faithfulness**, **Answer Relevancy**, **Context Precision**, **Context Recall**
- Score cards, bar chart, and per-question breakdown in the UI
- Results saved to `evaluation/ragas_results.json` and downloadable
- Requires `OPENAI_API_KEY` (uses GPT-4o for scoring)

### User Authentication
- Register and login with username + password
- Passwords hashed with **bcrypt** (auto-generated salt per user)
- Per-user chat history — sessions saved as JSON, browsable in the sidebar
- Session persistence across page reloads

### Feedback System
- Thumbs-up / thumbs-down on every AI response
- Logged to `feedback/feedback.jsonl` for future fine-tuning
- Approval rate summary in sidebar

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit ≥ 1.35 |
| LLM (main) | Groq — `llama-3.3-70b-versatile` |
| LLM (guard + HyDE) | Groq — `llama-3.1-8b-instant` |
| Vector database | ChromaDB ≥ 0.5 (persistent, cosine similarity) |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` |
| Hybrid search | `rank-bm25` |
| Reranking | Cohere — `rerank-english-v3.0` |
| Document parsing | PyMuPDF (PDF), python-docx (DOCX) |
| Text splitting | LangChain `RecursiveCharacterTextSplitter` |
| Evaluation | RAGAS + OpenAI GPT-4o |
| Auth | bcrypt |
| Config | python-dotenv |
| Container | Docker (Python 3.11-slim) |

---

## Project Structure

```
Enterprise-RAG-Chatbot/
│
├── enterprise-rag-chatbot/
│   ├── app/
│   │   ├── ui.py               # Streamlit UI — login, sidebar, 4 tabs
│   │   ├── rag_pipeline.py     # stream_answer(), generate_answer(), hallucination guard
│   │   ├── pyq_analyzer.py     # PYQ PDF analysis and multi-year comparison
│   │   ├── study_planner.py    # Day-by-day and multi-subject plan generation
│   │   └── feedback.py         # Thumbs up/down logging to JSONL
│   │
│   ├── ingestion/
│   │   └── ingest.py           # PDF/DOCX/TXT loader, chunker (512 tokens, 50 overlap), ChromaDB upsert
│   │
│   ├── retrieval/
│   │   └── retriever.py        # HyDE, vector search, BM25, RRF, Cohere reranking
│   │
│   ├── evaluation/
│   │   └── evaluate.py         # RAGAS runner — 7 test cases, saves ragas_results.json
│   │
│   ├── data/
│   │   └── sample_docs/        # Sample documents (hr_policy.txt, syllabus PDFs)
│   │
│   ├── chroma_db/              # Persistent ChromaDB vector store
│   ├── feedback/               # feedback.jsonl (gitignored)
│   ├── main.py                 # Entry point: streamlit run main.py
│   └── setup.py                # One-time project scaffold script
│
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Retrieval Architecture

```
User query
    │
    ▼
┌─────────────────────┐
│   HyDE Rewriting    │  llama-3.1-8b-instant generates a hypothetical answer
│   (optional)        │  → embeds the answer, not the raw query
└──────────┬──────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌─────────┐
│ Vector  │  │  BM25   │  Both run in parallel on the same ChromaDB collection
│ Search  │  │ Search  │
│ TOP_K=12│  │ TOP_K=12│
└────┬────┘  └────┬────┘
     └──────┬─────┘
            ▼
┌───────────────────────┐
│ Reciprocal Rank Fusion│  Merges both lists without weight tuning
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│   Cohere Reranking    │  rerank-english-v3.0, selects top 5 chunks
│   (optional)          │  Falls back to top-5 slice if no API key
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│  LLM Generation       │  llama-3.3-70b-versatile, streamed, max 700 tokens
│  (streaming)          │
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│  Hallucination Guard  │  llama-3.1-8b-instant checks every claim vs. context
│                       │  Flags answer if not grounded — shown in UI
└───────────────────────┘
```

---

## Installation

### Requirements
- Python 3.11+
- A free [Groq API key](https://console.groq.com) (required)
- A [Cohere API key](https://dashboard.cohere.com) (optional — enables reranking)
- An [OpenAI API key](https://platform.openai.com) (optional — only needed to run RAGAS evaluation)

### 1. Clone the repository

```bash
git clone https://github.com/KAKUL23FE10CSE00261/Enterprise-RAG-Chatbot.git
cd Enterprise-RAG-Chatbot/enterprise-rag-chatbot
```

### 2. Install dependencies

```bash
pip install -r ../requirements.txt
```

> First run downloads the `all-MiniLM-L6-v2` embedding model (~90 MB). This is a one-time download.

### 3. Set environment variables

Create a `.env` file in the `enterprise-rag-chatbot/` directory (copy from `.env.example` if present):

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional — enables Cohere reranking
COHERE_API_KEY=your_cohere_api_key_here

# Optional — only needed to run RAGAS evaluation
OPENAI_API_KEY=your_openai_api_key_here
```

Or set them in your terminal:

**Windows**
```bash
set GROQ_API_KEY=gsk_...
set COHERE_API_KEY=...        # optional
set OPENAI_API_KEY=sk-...     # optional
```

**Linux / macOS**
```bash
export GROQ_API_KEY=gsk_...
export COHERE_API_KEY=...     # optional
export OPENAI_API_KEY=sk-...  # optional
```

### 4. Run the app

```bash
streamlit run main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser. Register an account on the login screen to get started.

---

## Docker

### Build

```bash
docker build -t studymind-ai .
```

### Run

```bash
docker run -p 8501:8501 \
  -e GROQ_API_KEY=gsk_... \
  -e COHERE_API_KEY=... \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/feedback:/app/feedback \
  studymind-ai
```

The `-v` flags mount persistent volumes so your ingested documents and feedback survive container restarts.

---

## Usage

### 1. Upload and ingest documents

In the sidebar under **Documents → Upload & manage**:
- Select one or more PDF, DOCX, or TXT files
- Choose a document type tag (`syllabus`, `rules`, `pyq`, etc.)
- Click **⚡ Ingest files**

Ingestion chunks each document into 512-token segments with 50-token overlap and stores them in ChromaDB.

### 2. Ask questions

In the **💬 Chat** tab, type your question. Each answer includes:
- Streaming text response
- Source file citations
- A grounding badge (`✓ Verified` or `⚠ Verify manually`)
- 3 suggested follow-up questions

Use the **Summarise** button above the chat to get a structured overview of any ingested file.

### 3. Analyze PYQs

In the **📊 PYQ Analyzer** tab:
- Upload 1–3 years of previous year question PDFs
- Enter the subject name (e.g. `DBMS`, `Operating Systems`)
- Click **Analyze PYQs →**
- View topic frequency, predictions, difficulty assessment, and study tips
- Upload 2+ years to unlock the **Multi-Year Comparison**

### 4. Generate a study plan

In the **📅 Study Planner** tab:
- **Single Subject** — enter subject, exam date, daily hours, and difficulty level
- **Multiple Subjects** — add multiple subjects with exam dates and priorities for a combined weekly timetable

> Upload your syllabus PDF and ingest it first — the planner retrieves topic lists directly from ChromaDB.

### 5. Run RAGAS evaluation

In the **🧪 RAGAS Eval** tab:
- Toggle hybrid retrieval and HyDE on/off
- Click **▶ Run RAGAS Evaluation** (requires `OPENAI_API_KEY`)
- View faithfulness, answer relevancy, context precision, and context recall scores
- Download results as JSON

---

## Ingestion Details

| Setting | Value |
|---|---|
| Chunk size | 512 tokens |
| Chunk overlap | 50 tokens |
| Splitter | `RecursiveCharacterTextSplitter` with `["\n\n", "\n", ".", " "]` separators |
| Embedding model | `all-MiniLM-L6-v2` (384-dim) |
| Similarity metric | Cosine |
| Storage strategy | Upsert by `{stem}_chunk_{id}` — re-ingesting a file replaces existing chunks |
| Supported formats | `.pdf`, `.docx`, `.txt` |

---

## Evaluation — RAGAS Metrics

| Metric | What it measures |
|---|---|
| **Faithfulness** | Are all claims in the answer actually supported by the retrieved context? |
| **Answer Relevancy** | Does the answer address the question that was asked? |
| **Context Precision** | Are the retrieved chunks actually relevant to the question? |
| **Context Recall** | Did the retrieval capture everything needed to answer the question? |

To run evaluation manually from the command line:

```bash
cd enterprise-rag-chatbot
python -m evaluation.evaluate
```

Results are saved to `evaluation/ragas_results.json`.

---

## Environment Variables Reference

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | Yes | Powers all LLM calls (generation, HyDE, hallucination guard) |
| `COHERE_API_KEY` | No | Enables Cohere `rerank-english-v3.0` reranking — falls back to top-5 slice without it |
| `OPENAI_API_KEY` | No | Required only to run RAGAS evaluation (uses GPT-4o as judge) |

---

## Known Limitations

- **ChromaDB is local** — does not scale horizontally. For production use, replace with Pinecone or Qdrant.
- **File-based auth** — users stored in `data/users.json`. Replace with PostgreSQL + JWT for a multi-tenant deployment.
- **No async ingestion** — large documents block the UI during ingestion. A background worker (Celery) would fix this.
- **Rate limits** — three Groq API calls are made per query (HyDE + generation + hallucination guard). At free-tier limits this can cause rate limit errors under heavy use.
- **PDF text extraction only** — tables and images in PDFs are not extracted. Multi-modal RAG (vision models) would be needed for those.

---

## Future Improvements

- [ ] Deploy to Hugging Face Spaces (free) with a live URL
- [ ] Replace ChromaDB with Pinecone or Qdrant for scalability
- [ ] Async ingestion with Celery and Redis
- [ ] Multi-modal RAG — extract and index tables and figures from PDFs
- [ ] Calendar export from study planner (`.ics` format)
- [ ] Split `ui.py` into `auth.py`, `sidebar.py`, `chat.py`, `styles.py`
- [ ] Add unit tests for retriever and ingestion pipeline
- [ ] Chunking strategy comparison tab (fixed vs. semantic vs. sentence)

---

## Author

**Kakul Barsaiya**  
B.Tech CSE | AI/ML Enthusiast  
[GitHub](https://github.com/KAKUL23FE10CSE00261)
