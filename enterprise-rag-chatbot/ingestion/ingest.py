"""
ingestion/ingest.py — updated with delete_file() and absolute CHROMA_PATH
"""
import os
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
import fitz
from docx import Document

# Absolute path — works from any working directory or inside Docker
CHROMA_PATH     = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "enterprise_docs"
CHUNK_SIZE      = 512
CHUNK_OVERLAP   = 50


def load_pdf(path):
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)

def load_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def load_txt(path):
    return Path(path).read_text(encoding="utf-8")

LOADERS = {".pdf": load_pdf, ".docx": load_docx, ".txt": load_txt}

def load_document(path):
    ext = Path(path).suffix.lower()
    if ext not in LOADERS:
        raise ValueError(f"Unsupported file type: {ext}")
    return LOADERS[ext](path)

def chunk_text(text, source, filename, doc_type="general"):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "])
    chunks = splitter.split_text(text)
    ingested_at = datetime.utcnow().isoformat()
    return [{"text": c, "source": source, "filename": filename,
             "chunk_id": i, "doc_type": doc_type, "ingested_at": ingested_at}
            for i, c in enumerate(chunks)]

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2")
    return client.get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=ef,
        metadata={"hnsw:space": "cosine"})

def ingest_file(file_path, doc_type="general", original_filename=None):
    real_name = original_filename or Path(file_path).name
    print(f"Ingesting: {real_name} [{doc_type}]")
    text   = load_document(file_path)
    chunks = chunk_text(text, source=file_path, filename=real_name, doc_type=doc_type)
    col    = get_collection()
    stem   = Path(real_name).stem
    col.upsert(
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "filename": c["filename"],
                    "chunk_id": c["chunk_id"], "doc_type": c["doc_type"],
                    "ingested_at": c["ingested_at"]} for c in chunks],
        ids=[f"{stem}_chunk_{c['chunk_id']}" for c in chunks])
    print(f"  Stored {len(chunks)} chunks as '{real_name}'")
    return len(chunks)


def delete_file(filename: str) -> int:
    """Remove all chunks for a filename from ChromaDB. Returns number of chunks deleted."""
    col  = get_collection()
    data = col.get(where={"filename": filename}, include=["metadatas"])
    if not data["ids"]:
        return 0
    col.delete(ids=data["ids"])
    print(f"  Deleted {len(data['ids'])} chunks for '{filename}'")
    return len(data["ids"])


def get_full_text(filename: str) -> str:
    """Return full concatenated text for a specific ingested file."""
    try:
        col  = get_collection()
        data = col.get(where={"filename": filename},
                       include=["documents", "metadatas"])
        if not data["documents"]:
            return ""
        pairs = sorted(zip(data["metadatas"], data["documents"]),
                       key=lambda x: x[0].get("chunk_id", 0))
        return "\n".join(doc for _, doc in pairs)
    except Exception:
        return ""

def list_ingested_files() -> list[str]:
    try:
        col  = get_collection()
        data = col.get(include=["metadatas"])
        seen, names = set(), []
        for meta in data["metadatas"]:
            fn = meta.get("filename", "unknown")
            if fn not in seen:
                seen.add(fn); names.append(fn)
        return sorted(names)
    except Exception:
        return []