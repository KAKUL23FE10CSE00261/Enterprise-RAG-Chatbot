"""
backend/api.py — FastAPI backend for React Native app
Run: uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
"""
import os, sys, tempfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.ingest import ingest_file, list_ingested_files, get_full_text
from app.rag_pipeline import summarize_document, suggest_followups
from app.study_planner import generate_study_plan
from app.pyq_analyzer import analyze_pyq
from retrieval.retriever import retrieve

app = FastAPI(title="Enterprise RAG Chatbot API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    query: str
    history: list = []
    use_hyde: bool = True
    use_hybrid: bool = True
    doc_type_filter: Optional[str] = None

class StudyPlanRequest(BaseModel):
    subject: str
    exam_date: str
    hours_per_day: int = 4
    difficulty: str = "medium"

@app.get("/")
async def health():
    return {"status": "ok", "app": "Enterprise RAG Chatbot API"}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    from groq import Groq
    client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    chunks, rewritten_query = retrieve(req.query, use_hyde=req.use_hyde,
                                       use_hybrid=req.use_hybrid, doc_type_filter=req.doc_type_filter)
    if not chunks:
        return {"answer": "No relevant documents found. Please upload documents first.",
                "sources": [], "grounded": False, "chunks_used": 0,
                "rewritten_query": rewritten_query, "followups": []}
    context = "\n\n---\n\n".join(
        f"[{i+1}] (Source: {c.get('filename', c['source'].split('/')[-1])})\n{c['text']}"
        for i, c in enumerate(chunks))
    SYSTEM = """You are a helpful enterprise assistant.
Answer ONLY using the provided context.
If not in context say: I don't have enough information.
End with: Sources: [filename(s)]"""
    messages = [{"role": "system", "content": SYSTEM}]
    if req.history: messages.extend(req.history[-6:])
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {req.query}"})
    resp = client.chat.completions.create(model="llama-3.3-70b-versatile",
                                          messages=messages, temperature=0.2, max_tokens=700)
    answer = resp.choices[0].message.content.strip()
    seen, sources = set(), []
    for c in chunks:
        fn = c.get("filename", c["source"].split("/")[-1])
        if fn not in seen: seen.add(fn); sources.append(fn)
    guard = client.chat.completions.create(model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": f"Context:\n{context}\n\nAnswer:\n{answer}\n\nSupported? YES or NO only."}],
        max_tokens=5)
    grounded = guard.choices[0].message.content.strip().upper().startswith("YES")
    followups = []
    try: followups = suggest_followups(req.query, answer, sources)
    except Exception: pass
    return {"answer": answer, "sources": sources, "grounded": grounded,
            "chunks_used": len(chunks), "rewritten_query": rewritten_query, "followups": followups}

@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...), doc_type: str = Form("general")):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read()); path = tmp.name
    try:
        n = ingest_file(path, doc_type=doc_type, original_filename=file.filename)
        return {"success": True, "filename": file.filename, "chunks": n}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
    finally: os.unlink(path)

@app.get("/api/documents")
async def get_documents():
    return {"documents": list_ingested_files()}

@app.post("/api/summarize/{filename}")
async def summarize(filename: str):
    text = get_full_text(filename)
    if not text: raise HTTPException(status_code=404, detail="Document not found")
    return {"filename": filename, "summary": summarize_document(filename, text)}

@app.post("/api/study-plan")
async def study_plan(req: StudyPlanRequest):
    return generate_study_plan(req.subject, req.exam_date, req.hours_per_day, req.difficulty)

@app.post("/api/pyq-analyze")
async def pyq_analyze(file: UploadFile = File(...), subject: str = Form(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read()); path = tmp.name
    try: return analyze_pyq(path, subject, original_filename=file.filename)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
    finally: os.unlink(path)