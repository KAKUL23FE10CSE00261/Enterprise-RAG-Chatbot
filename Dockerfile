# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch first (saves ~2GB vs GPU version)
RUN pip install --no-cache-dir --prefix=/install \
    torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu

# Install remaining packages (torch already satisfied)
RUN pip install --no-cache-dir --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app

COPY Enterprise-RAG-Chatbot/ ./enterprise-rag-chatbot/

RUN mkdir -p \
    /app/enterprise-rag-chatbot/chroma_db \
    /app/enterprise-rag-chatbot/feedback \
    /app/enterprise-rag-chatbot/data/sample_docs \
    /app/enterprise-rag-chatbot/data/chat_history

VOLUME ["/app/enterprise-rag-chatbot/chroma_db", "/app/enterprise-rag-chatbot/feedback"]

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "enterprise-rag-chatbot/main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]