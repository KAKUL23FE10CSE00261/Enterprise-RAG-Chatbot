FROM python:3.11-slim

WORKDIR /app

# System deps for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ChromaDB persistence volume
VOLUME ["/app/chroma_db", "/app/feedback"]

EXPOSE 8501

ENV PYTHONUNBUFFERED=1

CMD ["streamlit", "run", "enterprise-rag-chatbot/main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]