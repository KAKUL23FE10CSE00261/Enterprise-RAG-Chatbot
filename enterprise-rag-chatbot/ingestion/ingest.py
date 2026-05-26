"""
ingestion/ingest.py

Fixes applied:
  1. Chunk IDs are collision-safe: {stem}_{sha1_of_text[:8]}_chunk_{i}
     Two ingestions of the same filename no longer silently corrupt chunks.
  2. URL ingestion added: ingest_url(url, doc_type) uses requests + BeautifulSoup.
  3. retriever.invalidate_collection_cache() called after every write so the
     BM25 index and ChromaDB singleton are refreshed automatically.
  4. list_ingested_files() returns (filename, chunk_count, ingested_at) tuples
     so the UI can display richer info.
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
import fitz
from docx import Document

CHROMA_PATH     = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "enterprise_docs"
CHUNK_SIZE      = 512
CHUNK_OVERLAP   = 50


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_pdf(path: str) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def load_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def load_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_url(url: str) -> str:
    """
    Fetch a web page and extract its readable text.
    Requires: pip install requests beautifulsoup4 lxml
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError(
            "URL ingestion requires 'requests' and 'beautifulsoup4'. "
            "Run: pip install requests beautifulsoup4 lxml"
        ) from exc

    headers = {"User-Agent": "Mozilla/5.0 (compatible; StudyMindRAG/1.0)"}
    resp    = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Remove boilerplate elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Prefer <article> or <main>; fall back to <body>
    content = (
        soup.find("article")
        or soup.find("main")
        or soup.find("body")
        or soup
    )
    return content.get_text(separator="\n", strip=True)


LOADERS = {".pdf": load_pdf, ".docx": load_docx, ".txt": load_txt}


def load_document(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext not in LOADERS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {list(LOADERS)}")
    return LOADERS[ext](path)


# ── Chunking ──────────────────────────────────────────────────────────────────

def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def chunk_text(text: str, source: str, filename: str, doc_type: str = "general") -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks      = splitter.split_text(text)
    ingested_at = datetime.utcnow().isoformat()
    stem        = Path(filename).stem

    return [
        {
            "text":         c,
            "source":       source,
            "filename":     filename,
            "chunk_id":     i,
            # Collision-safe ID: stem + content hash + index
            "id":           f"{stem}_{_sha1(c)[:8]}_chunk_{i}",
            "doc_type":     doc_type,
            "ingested_at":  ingested_at,
        }
        for i, c in enumerate(chunks)
    ]


# ── ChromaDB helpers ──────────────────────────────────────────────────────────

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef     = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def _invalidate_retriever_cache() -> None:
    """Signal retriever module to drop its singletons."""
    try:
        from retrieval.retriever import invalidate_collection_cache
        invalidate_collection_cache()
    except Exception:
        pass  # retriever may not be importable in test environments


# ── Ingest file ───────────────────────────────────────────────────────────────

def ingest_file(
    file_path: str,
    doc_type: str = "general",
    original_filename: str | None = None,
) -> int:
    real_name = original_filename or Path(file_path).name
    print(f"Ingesting: {real_name} [{doc_type}]")

    text   = load_document(file_path)
    chunks = chunk_text(text, source=file_path, filename=real_name, doc_type=doc_type)
    col    = get_collection()

    col.upsert(
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "source":       c["source"],
                "filename":     c["filename"],
                "chunk_id":     c["chunk_id"],
                "doc_type":     c["doc_type"],
                "ingested_at":  c["ingested_at"],
            }
            for c in chunks
        ],
        ids=[c["id"] for c in chunks],
    )
    print(f"  Stored {len(chunks)} chunks as '{real_name}'")
    _invalidate_retriever_cache()
    return len(chunks)


# ── Ingest URL ────────────────────────────────────────────────────────────────

def ingest_url(url: str, doc_type: str = "general") -> int:
    """
    Fetch a URL and ingest its text content into ChromaDB.
    Returns the number of chunks stored.
    """
    print(f"Ingesting URL: {url} [{doc_type}]")
    text = load_url(url)
    if not text.strip():
        raise ValueError("No readable text extracted from URL")

    # Use the URL as both source and a short display filename
    display_name = url.split("//")[-1].split("?")[0][:60]
    chunks       = chunk_text(text, source=url, filename=display_name, doc_type=doc_type)
    col          = get_collection()

    col.upsert(
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "source":       c["source"],
                "filename":     c["filename"],
                "chunk_id":     c["chunk_id"],
                "doc_type":     c["doc_type"],
                "ingested_at":  c["ingested_at"],
            }
            for c in chunks
        ],
        ids=[c["id"] for c in chunks],
    )
    print(f"  Stored {len(chunks)} chunks from '{url}'")
    _invalidate_retriever_cache()
    return len(chunks)


# ── Delete file ───────────────────────────────────────────────────────────────

def delete_file(filename: str) -> int:
    """Remove all chunks for a filename from ChromaDB. Returns number of chunks deleted."""
    col  = get_collection()
    data = col.get(where={"filename": filename}, include=["metadatas"])
    if not data["ids"]:
        return 0
    col.delete(ids=data["ids"])
    print(f"  Deleted {len(data['ids'])} chunks for '{filename}'")
    _invalidate_retriever_cache()
    return len(data["ids"])


# ── Query helpers ─────────────────────────────────────────────────────────────

def get_full_text(filename: str) -> str:
    """Return full concatenated text for a specific ingested file."""
    try:
        col  = get_collection()
        data = col.get(
            where={"filename": filename},
            include=["documents", "metadatas"],
        )
        if not data["documents"]:
            return ""
        pairs = sorted(
            zip(data["metadatas"], data["documents"]),
            key=lambda x: x[0].get("chunk_id", 0),
        )
        return "\n".join(doc for _, doc in pairs)
    except Exception:
        return ""


def list_ingested_files() -> list[dict]:
    """
    Returns a list of dicts:
      {"filename": str, "chunk_count": int, "doc_type": str, "ingested_at": str}
    Sorted alphabetically by filename.
    """
    try:
        col  = get_collection()
        data = col.get(include=["metadatas"])
        seen: dict[str, dict] = {}
        for meta in data["metadatas"]:
            fn = meta.get("filename", "unknown")
            if fn not in seen:
                seen[fn] = {
                    "filename":    fn,
                    "chunk_count": 0,
                    "doc_type":    meta.get("doc_type", "general"),
                    "ingested_at": meta.get("ingested_at", ""),
                }
            seen[fn]["chunk_count"] += 1
        return sorted(seen.values(), key=lambda x: x["filename"])
    except Exception:
        return []


def list_ingested_filenames() -> list[str]:
    """Convenience wrapper — returns just the filenames (backwards-compatible)."""
    return [f["filename"] for f in list_ingested_files()]