"""
Document ingestion pipeline.
Supports PDF, DOCX, and TXT files.
Chunks text, generates embeddings, and stores in ChromaDB.
"""

import os
from pathlib import Path
from typing import List

import chromadb
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz  # PyMuPDF
from docx import Document


CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "enterprise_docs"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
EMBED_MODEL = "text-embedding-3-small"  # swap to "BAAI/bge-m3" for local


def load_pdf(path: str) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def load_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def load_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_document(path: str) -> str:
    ext = Path(path).suffix.lower()
    loaders = {".pdf": load_pdf, ".docx": load_docx, ".txt": load_txt}
    if ext not in loaders:
        raise ValueError(f"Unsupported file type: {ext}")
    return loaders[ext](path)


def chunk_text(text: str, source: str) -> List[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_text(text)
    return [
        {"text": chunk, "source": source, "chunk_id": i}
        for i, chunk in enumerate(chunks)
    ]


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=EMBED_MODEL,
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"},
    )


def ingest_file(file_path: str):
    print(f"Ingesting: {file_path}")
    text = load_document(file_path)
    chunks = chunk_text(text, source=file_path)

    collection = get_collection()
    collection.upsert(
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks],
        ids=[f"{Path(file_path).stem}_chunk_{c['chunk_id']}" for c in chunks],
    )
    print(f"  Stored {len(chunks)} chunks from {Path(file_path).name}")


def ingest_folder(folder_path: str):
    folder = Path(folder_path)
    files = list(folder.glob("**/*.pdf")) + \
            list(folder.glob("**/*.docx")) + \
            list(folder.glob("**/*.txt"))
    for f in files:
        ingest_file(str(f))
    print(f"\nDone. Ingested {len(files)} files.")


if __name__ == "__main__":
    ingest_folder("data/sample_docs")