"""
app/pyq_analyzer.py

Fixes applied:
  1. In-memory cache (by file path + mtime) — re-analysing the same PDF
     no longer makes a redundant API call.
  2. Text truncation raised from 8000 → 14000 chars (covers most PYQ papers).
  3. JSON-based structured output replaces fragile regex parsing:
     the model now returns valid JSON that we parse safely with a fallback.
  4. compare_pyqs handles edge cases (< 2 analyses) gracefully.
"""

import hashlib
import os
import re
import json
import tempfile
import threading
from pathlib import Path

import fitz  # PyMuPDF
from groq import Groq, APIError, RateLimitError, APITimeoutError, APIConnectionError

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# ── In-memory cache ───────────────────────────────────────────────────────────
# Key: sha1(first 20 KB of pdf bytes) — stable even if tmp path changes
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


def _file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha1(f.read(20_480)).hexdigest()


# ── PDF text extraction ───────────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    doc  = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


# ── Analysis ──────────────────────────────────────────────────────────────────

_JSON_PROMPT = """Analyze this exam paper and return ONLY valid JSON (no markdown fences) with this exact schema:
{
  "topics": [{"name": "string", "question_count": integer}],
  "frequently_asked": ["string", ...],
  "predictions": ["string", ...],
  "difficulty": "Easy|Medium|Hard",
  "difficulty_explanation": "string",
  "study_advice": ["string", ...]
}
Rules:
- topics: all distinct topic areas found, with question counts
- frequently_asked: top 5 specific concepts that appear most
- predictions: top 5 topics likely to appear in next exam
- study_advice: exactly 3 actionable tips
Return ONLY the JSON object, nothing else."""


def _parse_json_response(text: str) -> dict:
    """Safely parse JSON from model output. Returns {} on failure."""
    # Strip markdown fences if the model adds them despite instructions
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Best-effort: find first {...} block
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return {}


def analyze_pyq(
    file_path: str,
    subject_name: str,
    original_filename: str | None = None,
) -> dict:
    """
    Analyse a PYQ PDF.

    Returns:
      filename, subject, analysis (raw text), chart_data (dict),
      predictions (list), topics (list), difficulty, study_advice
    """
    fname  = original_filename or os.path.basename(file_path)
    fhash  = _file_hash(file_path)
    cache_key = f"{fhash}:{subject_name}"

    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]

    text        = extract_text_from_pdf(file_path)
    # Raised from 8 000 → 14 000 chars to cover longer PYQ papers
    text_sample = text[:14_000] + ("..." if len(text) > 14_000 else "")

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _JSON_PROMPT},
                {"role": "user",   "content": (
                    f"Subject: {subject_name}\nFile: {fname}\n\n"
                    f"Exam paper text:\n{text_sample}"
                )},
            ],
            temperature=0.15,
            max_tokens=1500,
            timeout=60,
        )
        raw = resp.choices[0].message.content.strip()
    except RateLimitError:
        return {"error": "⚠️ Groq rate limit reached. Please wait a moment and try again."}
    except APITimeoutError:
        return {"error": "⚠️ Request timed out. Please try again."}
    except APIConnectionError:
        return {"error": "⚠️ Could not connect to Groq API. Check your GROQ_API_KEY."}
    except APIError as e:
        return {"error": f"⚠️ Groq API error: {str(e)}"}
    except Exception as e:
        return {"error": f"⚠️ Unexpected error: {str(e)}"}

    parsed = _parse_json_response(raw)

    # Build chart_data from structured JSON (not regex)
    chart_data: dict[str, int] = {}
    for t in parsed.get("topics", []):
        name  = t.get("name", "").strip()
        count = t.get("question_count", 0)
        if name and isinstance(count, (int, float)) and count > 0:
            chart_data[name] = int(count)

    if not chart_data:
        chart_data = {"Analysis complete": 1}

    result = {
        "filename":       fname,
        "subject":        subject_name,
        "analysis":       raw,                              # kept for backward compat
        "parsed":         parsed,                           # structured data
        "chart_data":     chart_data,
        "predictions":    [p for p in parsed.get("predictions", []) if p][:5],
        "frequently_asked": [f for f in parsed.get("frequently_asked", []) if f][:6],
        "difficulty":     parsed.get("difficulty", "Medium"),
        "difficulty_explanation": parsed.get("difficulty_explanation", ""),
        "study_advice":   [a for a in parsed.get("study_advice", []) if a][:3],
        "total_text_len": len(text),
    }

    with _cache_lock:
        _cache[cache_key] = result

    return result


# ── Multi-year comparison ─────────────────────────────────────────────────────

def compare_pyqs(analyses: list[dict]) -> str:
    if len(analyses) < 2:
        return "Please upload at least 2 PYQ papers to compare."

    summaries = "\n\n".join(
        f"=== {a['filename']} ===\n{a['analysis'][:1000]}"
        for a in analyses
    )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert exam analyst."},
                {"role": "user",   "content": (
                    f"Compare these {len(analyses)} PYQ analyses and identify:\n\n"
                    f"{summaries}\n\n"
                    "1. Topics that appear EVERY year (must prepare)\n"
                    "2. Topics that appeared recently (likely this year)\n"
                    "3. Topics that have not appeared yet (might come)\n"
                    "4. Overall trend in question difficulty\n"
                    "5. Final prediction: Top 5 topics for next exam"
                )},
            ],
            temperature=0.3,
            max_tokens=900,
            timeout=60,
        )
        return resp.choices[0].message.content.strip()
    except RateLimitError:
        return "⚠️ Rate limit reached during comparison. Please wait a moment."
    except APITimeoutError:
        return "⚠️ Comparison timed out. Please try again."
    except (APIConnectionError, APIError) as e:
        return f"⚠️ API error: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"