# 🚀 Enterprise RAG Chatbot

An advanced Retrieval-Augmented Generation (RAG) chatbot built with Streamlit, Hybrid Retrieval, ChromaDB, and LLMs to provide accurate, context-aware, and grounded responses from uploaded documents.

Users can upload PDFs and documents, ask questions in natural language, analyze previous year question papers, generate study plans, and receive intelligent responses with source-backed retrieval.

---

## ✨ Features

### 📚 Intelligent Document Chat
- Upload PDF, DOCX, TXT documents
- Ask questions in natural language
- Source-grounded responses
- Streaming answers like ChatGPT

### 🔍 Advanced Retrieval Pipeline
- Hybrid Retrieval:
  - Dense vector search (ChromaDB)
  - BM25 keyword search
- Reciprocal Rank Fusion (RRF)
- HyDE query rewriting
- Cohere reranking

### 🛡️ Hallucination Guard
- Secondary validation for response grounding
- Reduces unsupported responses

### 📊 PYQ Analyzer
- Upload Previous Year Question papers
- Analyze repeated topics
- Identify important concepts
- Generate topic insights

### 📅 Smart Study Planner
- Personalized study schedule generation
- Helps organize preparation workflow

### 👍 Feedback System
- Like/dislike response system
- Feedback logging for future improvement

### 📱 WhatsApp Integration
- WhatsApp bot support
- Access chatbot outside the web interface

### 🐳 Deployment Ready
- Docker support
- Streamlit deployment support

---

# 🏗️ System Architecture

```text
                    User Query
                         │
                         ▼
                ┌────────────────┐
                │ Streamlit UI   │
                └────────┬───────┘
                         │
                         ▼
               ┌──────────────────┐
               │ HyDE Rewriting   │
               └────────┬─────────┘
                        │
          ┌─────────────┴────────────┐
          │                          │
          ▼                          ▼
 ┌─────────────────┐      ┌────────────────┐
 │ Vector Search   │      │ BM25 Search    │
 │ ChromaDB        │      │ Keyword Search │
 └────────┬────────┘      └───────┬────────┘
          │                       │
          └──────────┬────────────┘
                     ▼
        ┌────────────────────────┐
        │ Reciprocal Rank Fusion │
        └──────────┬─────────────┘
                   ▼
        ┌────────────────────────┐
        │ Cohere Reranking       │
        └──────────┬─────────────┘
                   ▼
        ┌────────────────────────┐
        │ LLM Response Generation│
        └──────────┬─────────────┘
                   ▼
        ┌────────────────────────┐
        │ Grounded Response      │
        └────────────────────────┘
```

---

# 📂 Project Structure

```bash
Enterprise-RAG-Chatbot/
│
├── app/
│   ├── ui.py
│   ├── rag_pipeline.py
│   ├── pyq_analyzer.py
│   ├── study_planner.py
│   └── feedback.py
│
├── ingestion/
│   └── ingest.py
│
├── retrieval/
│   └── retriever.py
│
├── evaluation/
│
├── whatsapp_bot/
│
├── feedback/
│
├── chroma_db/
│
├── data/
│
├── main.py
├── setup.py
├── Dockerfile
└── README.md
```

---

# ⚙️ Tech Stack

| Category | Technology |
|------------|-------------|
| Frontend | Streamlit |
| LLM | Groq API |
| Vector Database | ChromaDB |
| Embeddings | Sentence Transformers |
| Retrieval | BM25 |
| Reranking | Cohere |
| Document Parsing | PyMuPDF |
| Evaluation | RAGAS |
| Deployment | Docker |

---

# 🚀 Installation

Clone repository:

```bash
git clone https://github.com/KAKUL23FE10CSE00261/Enterprise-RAG-Chatbot.git

cd Enterprise-RAG-Chatbot
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set environment variables:

Windows:

```bash
set GROQ_API_KEY=your_api_key

set COHERE_API_KEY=your_api_key
```

Linux/Mac:

```bash
export GROQ_API_KEY=your_api_key

export COHERE_API_KEY=your_api_key
```

Run application:

```bash
streamlit run main.py
```

---

# 🐳 Docker Setup

Build image:

```bash
docker build -t enterprise-rag .
```

Run container:

```bash
docker run -p 8501:8501 enterprise-rag
```

---

# 📸 Application Modules

### 💬 Chat Module
- Ask questions from uploaded documents
- Streaming responses
- Citation support

### 📊 PYQ Analyzer
- Analyze previous year papers
- Identify patterns and trends

### 📅 Study Planner
- Personalized preparation planning

### 📱 WhatsApp Bot
- Access chatbot through WhatsApp

---

# 🔮 Future Improvements

- [ ] Multi-modal RAG
- [ ] Authentication system
- [ ] Redis caching
- [ ] Cloud deployment
- [ ] Pinecone integration
- [ ] Analytics dashboard

---

# 👩‍💻 Author

Kakul Barsaiya

AI/ML Enthusiast | Data Science Learner | Building real-world ML applications 🚀
