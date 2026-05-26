"""
app/feedback.py

Fixes applied:
  1. threading.Lock around every file write → safe under Streamlit's
     threaded execution model (multiple users writing simultaneously
     no longer risks JSONL corruption).
  2. load_feedback() is now robust to malformed lines (skips, not crashes).
  3. feedback_summary() exposes per-day trend data for a future analytics UI.
"""

import json
import os
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FEEDBACK_DIR  = Path(__file__).parent.parent / "feedback"
FEEDBACK_PATH = FEEDBACK_DIR / "feedback.jsonl"

_write_lock = threading.Lock()


# ── Write ─────────────────────────────────────────────────────────────────────

def log_feedback(
    query:   str,
    answer:  str,
    sources: list[str],
    rating:  str,        # "up" or "down"
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
    # Lock prevents concurrent writes from corrupting the JSONL file
    with _write_lock:
        with open(FEEDBACK_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── Read ──────────────────────────────────────────────────────────────────────

def load_feedback() -> list[dict]:
    if not FEEDBACK_PATH.exists():
        return []
    records: list[dict] = []
    with open(FEEDBACK_PATH, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[feedback] Skipping malformed line {lineno}")
    return records


# ── Summary ───────────────────────────────────────────────────────────────────

def feedback_summary() -> dict:
    """
    Returns overall stats plus a daily_trend list (last 7 days):
      [{"date": "YYYY-MM-DD", "up": N, "down": M}, ...]
    """
    records = load_feedback()
    total   = len(records)
    up      = sum(1 for r in records if r.get("rating") == "up")
    down    = total - up

    # Build daily trend
    daily: dict[str, dict] = defaultdict(lambda: {"up": 0, "down": 0})
    for r in records:
        ts = r.get("timestamp", "")[:10]  # "YYYY-MM-DD"
        if ts:
            daily[ts]["up" if r.get("rating") == "up" else "down"] += 1

    # Sort last 7 days
    sorted_days = sorted(daily.keys())[-7:]
    daily_trend = [{"date": d, **daily[d]} for d in sorted_days]

    return {
        "total":         total,
        "thumbs_up":     up,
        "thumbs_down":   down,
        "approval_rate": round(up / total * 100, 1) if total else 0,
        "daily_trend":   daily_trend,
    }