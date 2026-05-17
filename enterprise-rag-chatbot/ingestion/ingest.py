import os
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
import fitz
from docx import Document

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "enterprise_docs"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
EMBED_MODEL = "text-embedding-3-small"

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

def chunk_text(text, source, doc_type="general"):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_text(text)
    filename = Path(source).name
    ingested_at = datetime.utcnow().isoformat()
    return [
        {
            "text": c,
            "source": source,
            "filename": filename,
            "chunk_id": i,
            "doc_type": doc_type,
            "ingested_at": ingested_at,
        }
        for i, c in enumerate(chunks)
    ]

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=EMBED_MODEL,
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

def ingest_file(file_path, doc_type="general"):
    print(f"Ingesting: {file_path} [{doc_type}]")
    text = load_document(file_path)
    chunks = chunk_text(text, source=file_path, doc_type=doc_type)
    collection = get_collection()
    stem = Path(file_path).stem
    collection.upsert(
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "source": c["source"],
                "filename": c["filename"],
                "chunk_id": c["chunk_id"],
                "doc_type": c["doc_type"],
                "ingested_at": c["ingested_at"],
            }
            for c in chunks
        ],
        ids=[f"{stem}_chunk_{c['chunk_id']}" for c in chunks],
    )
    print(f"  Stored {len(chunks)} chunks")
    return len(chunks)

def list_ingested_files():
    try:
        col = get_collection()
        data = col.get(include=["metadatas"])
        seen, names = set(), []
        for meta in data["metadatas"]:
            fn = meta.get("filename", "unknown")
            if fn not in seen:
                seen.add(fn)
                names.append(fn)
        return sorted(names)
    except Exception:
        return []

if __name__ == "__main__":
    from ingestion.ingest import ingest_file
    ingest_file("data/sample_docs/hr_policy.txt")