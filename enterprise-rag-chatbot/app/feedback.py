"""
app/feedback.py
Logs thumbs-up / thumbs-down feedback to a JSONL file for future fine-tuning.
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Absolute path — works from any working directory or inside Docker
FEEDBACK_DIR  = Path(__file__).parent.parent / "feedback"
FEEDBACK_PATH = FEEDBACK_DIR / "feedback.jsonl"


def log_feedback(
    query: str,
    answer: str,
    sources: list[str],
    rating: str,          # "up" or "down"
    comment: str = "",
) -> None:
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "query":     query,
        "answer":    answer,
        "sources":   sources,
        "rating":    rating,
        "comment":   comment,
    }
    with open(FEEDBACK_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_feedback() -> list[dict]:
    if not FEEDBACK_PATH.exists():
        return []
    records = []
    with open(FEEDBACK_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def feedback_summary() -> dict:
    records = load_feedback()
    total = len(records)
    up    = sum(1 for r in records if r["rating"] == "up")
    down  = total - up
    return {"total": total, "thumbs_up": up, "thumbs_down": down,
            "approval_rate": round(up / total * 100, 1) if total else 0}
