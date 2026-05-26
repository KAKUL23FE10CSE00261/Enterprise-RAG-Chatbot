"""
setup.py
Run this once after cloning to create all required folders and placeholder files.

Usage:
    cd enterprise-rag-chatbot
    python setup.py
"""

import os
from pathlib import Path

BASE = Path(__file__).parent

FOLDERS = [
    "app",
    "ingestion",
    "retrieval",
    "evaluation",
    "data/sample_docs",
    "data/chat_history",
    "chroma_db",
    "feedback",
]

for folder in FOLDERS:
    (BASE / folder).mkdir(parents=True, exist_ok=True)
    print(f"  created  {folder}/")

for init in ["app/__init__.py", "ingestion/__init__.py",
             "retrieval/__init__.py", "evaluation/__init__.py"]:
    p = BASE / init
    if not p.exists():
        p.write_text("")
        print(f"  created  {init}")

feedback_file = BASE / "feedback" / "feedback.jsonl"
if not feedback_file.exists():
    feedback_file.write_text("")
    print(f"  created  feedback/feedback.jsonl")

print("\nSetup complete.")
print("\nNext steps:")
print("  1. Copy .env.example to .env and fill in your API keys")
print("  2. pip install -r ../requirements.txt")
print("  3. streamlit run main.py")
