import os
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
    return "\n".join(page.get_text() for page in doc)

def load_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

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
        separators=["\n\n", "\n", ".", " "],
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
        ids=[f"{Path(file_path).stem}_chunk_{c['chunk_id']}" for c in chunks])
    print(f"  Stored {len(chunks)} chunks")

def ingest_folder(folder_path):
    folder = Path(folder_path)
    files = list(folder.glob("**/*.pdf")) + list(folder.glob("**/*.docx")) + list(folder.glob("**/*.txt"))
    for f in files:
        ingest_file(str(f))
    print(f"Done. Ingested {len(files)} files.")

if __name__ == "__main__":
    ingest_folder("data/sample_docs")
