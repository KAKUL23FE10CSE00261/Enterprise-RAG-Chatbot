"""
app/pyq_analyzer.py
Analyzes Previous Year Questions (PYQ) PDFs to find:
- Most frequently asked topics
- Topic-wise question distribution
- Predicted important topics for next exam
"""

import os
import re
from collections import Counter
from groq import Groq
import fitz  # PyMuPDF

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


def extract_text_from_pdf(file_path):
    """Extract all text from a PDF."""
    doc  = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def analyze_pyq(file_path, subject_name, original_filename=None):
    """
    Analyze a PYQ PDF and return topic frequency + predictions.

    Returns dict with:
      - topics: list of (topic, frequency) tuples
      - analysis: full Groq analysis text
      - predictions: predicted important topics
      - chart_data: data for Streamlit bar chart
    """
    fname = original_filename or os.path.basename(file_path)
    text  = extract_text_from_pdf(file_path)

    # Truncate to avoid token limits
    text_sample = text[:8000] + ("..." if len(text) > 8000 else "")

    # ── Step 1: Extract and categorize questions ──────────────────────────────
    extract_resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content":
             "You are an expert at analyzing exam papers. "
             "Extract and categorize questions by topic."},
            {"role": "user", "content":
             f"Analyze this {subject_name} PYQ paper: '{fname}'\n\n"
             f"Text:\n{text_sample}\n\n"
             "Return a JSON-like analysis in this EXACT format:\n\n"
             "TOPICS:\n"
             "- TopicName: X questions\n"
             "- TopicName: X questions\n"
             "(list all topics found)\n\n"
             "FREQUENTLY_ASKED:\n"
             "(top 5 most repeated questions/concepts)\n\n"
             "PREDICTIONS:\n"
             "(top 5 topics likely to appear in next exam based on frequency)\n\n"
             "DIFFICULTY:\n"
             "(overall difficulty: Easy/Medium/Hard + explanation)\n\n"
             "STUDY_ADVICE:\n"
             "(3 specific tips based on this PYQ analysis)"}
        ],
        temperature=0.2,
        max_tokens=1200,
    )

    analysis_text = extract_resp.choices[0].message.content.strip()

    # ── Step 2: Parse topic frequencies for chart ─────────────────────────────
    chart_data = {}
    topic_section = False
    for line in analysis_text.split("\n"):
        if "TOPICS:" in line:
            topic_section = True
            continue
        if topic_section and line.startswith("- "):
            # Parse "- TopicName: X questions"
            match = re.match(r"-\s+(.+?):\s+(\d+)\s+question", line)
            if match:
                topic = match.group(1).strip()
                count = int(match.group(2))
                chart_data[topic] = count
        if topic_section and line.strip() == "":
            if chart_data:  # stop after first empty line after topics
                topic_section = False

    # Fallback: if parsing failed, create dummy data from text
    if not chart_data:
        chart_data = {"Analysis Complete": 1}

    # ── Step 3: Extract predictions ───────────────────────────────────────────
    predictions = []
    in_pred = False
    for line in analysis_text.split("\n"):
        if "PREDICTIONS:" in line:
            in_pred = True
            continue
        if in_pred and line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "-")):
            pred = re.sub(r"^[\d\.\-\s]+", "", line).strip()
            if pred:
                predictions.append(pred)
        if in_pred and "DIFFICULTY:" in line:
            break

    return {
        "filename":    fname,
        "subject":     subject_name,
        "analysis":    analysis_text,
        "chart_data":  chart_data,
        "predictions": predictions[:5],
        "total_text_len": len(text),
    }


def compare_pyqs(analyses):
    """
    Compare multiple years' PYQ analyses to find consistent patterns.
    analyses: list of analysis dicts from analyze_pyq()
    """
    if len(analyses) < 2:
        return "Upload at least 2 PYQ papers to compare."

    summaries = "\n\n".join(
        f"=== {a['filename']} ===\n{a['analysis'][:800]}"
        for a in analyses
    )

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an expert exam analyst."},
            {"role": "user",   "content":
             f"Compare these {len(analyses)} PYQ analyses and identify:\n\n"
             f"{summaries}\n\n"
             "1. Topics that appear EVERY year (must prepare)\n"
             "2. Topics that appeared recently (likely this year)\n"
             "3. Topics that haven't appeared yet (might come)\n"
             "4. Overall trend in question difficulty\n"
             "5. Final prediction: Top 5 topics for next exam"}
        ],
        temperature=0.3,
        max_tokens=800,
    )
    return resp.choices[0].message.content.strip()