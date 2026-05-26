"""
app/study_planner.py

Fixes applied:
  1. Generated plans are cached in memory (key = subject+date+hours+difficulty)
     so repeated button clicks don't waste API calls.
  2. generate_ics() exports a study plan as an iCalendar (.ics) file so
     users can import directly into Google Calendar / Apple Calendar / Outlook.
  3. generate_multi_subject_plan error handling made consistent with single plan.
"""

import hashlib
import os
import re
import threading
from datetime import datetime, timedelta

from groq import Groq, APIError, RateLimitError, APITimeoutError, APIConnectionError
from retrieval.retriever import retrieve

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# ── In-memory plan cache ──────────────────────────────────────────────────────
_plan_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


def _cache_key(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()


# ── Syllabus retrieval ────────────────────────────────────────────────────────

def get_syllabus_topics(subject: str) -> str:
    chunks, _ = retrieve(
        f"syllabus topics units {subject}",
        use_hyde=False,
        use_hybrid=True,
    )
    if not chunks:
        return f"No syllabus found for {subject}. Please upload the syllabus PDF first."
    return "\n".join(c["text"] for c in chunks[:5])


# ── Single-subject plan ───────────────────────────────────────────────────────

def generate_study_plan(
    subject:        str,
    exam_date_str:  str,
    hours_per_day:  int,
    difficulty:     str = "medium",
) -> dict:
    today     = datetime.today().date()
    exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    days_left = (exam_date - today).days

    if days_left <= 0:
        return {"error": "Exam date must be in the future."}

    key = _cache_key(subject, exam_date_str, hours_per_day, difficulty)
    with _cache_lock:
        if key in _plan_cache:
            return _plan_cache[key]

    syllabus    = get_syllabus_topics(subject)
    total_hours = days_left * hours_per_day

    prompt = f"""Create a detailed day-by-day study plan for a student.

Subject: {subject}
Days until exam: {days_left}
Study hours per day: {hours_per_day}
Total available hours: {total_hours}
Difficulty level: {difficulty}
Exam date: {exam_date_str}
Today: {today}

Syllabus/Topics available:
{syllabus}

Create a structured study plan with this EXACT format:

## 📅 Study Plan for {subject}
**Exam Date:** {exam_date_str} | **Days Left:** {days_left} | **Total Hours:** {total_hours}

## 📊 Strategy
(2-3 sentences on approach based on days left)

## 📆 Day-by-Day Schedule
(List each day: Day N (Date) | Topics | Hours | Focus)

## ⚠️ Priority Topics
(Top 5 most important topics)

## 💡 Study Tips for {subject}
(3 specific tips)

## ✅ Revision Plan (Last 2 days)
(What to do in final 2 days before exam)

Be specific and realistic. If days are few, focus on high-priority topics only."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert academic advisor creating personalised study plans."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
            timeout=45,
        )
        plan_text = resp.choices[0].message.content.strip()
    except RateLimitError:
        return {"error": "⚠️ Groq rate limit reached. Please wait a moment and try again."}
    except APITimeoutError:
        return {"error": "⚠️ Request timed out. Please try again."}
    except (APIConnectionError, APIError) as e:
        return {"error": f"⚠️ API error: {str(e)}"}
    except Exception as e:
        return {"error": f"⚠️ Unexpected error: {str(e)}"}

    result = {
        "subject":       subject,
        "exam_date":     exam_date_str,
        "days_left":     days_left,
        "hours_per_day": hours_per_day,
        "total_hours":   total_hours,
        "plan":          plan_text,
    }

    with _cache_lock:
        _plan_cache[key] = result

    return result


# ── iCalendar export ──────────────────────────────────────────────────────────

def generate_ics(plan_result: dict) -> str:
    """
    Convert a study plan dict into an iCalendar (.ics) string.
    Each 'Day N' block in the plan becomes a VEVENT.
    Import the output into Google Calendar, Outlook, or Apple Calendar.
    """
    subject      = plan_result.get("subject", "Study")
    exam_date    = plan_result.get("exam_date", "")
    hours_per_day = plan_result.get("hours_per_day", 3)
    plan_text    = plan_result.get("plan", "")

    # Parse "Day N (YYYY-MM-DD)" lines from the plan
    day_pattern = re.compile(
        r"Day\s+(\d+)\s*\((\d{4}-\d{2}-\d{2})\)[^\n]*\|([^\n]*)\|([^\n]*)\|([^\n]*)",
        re.IGNORECASE,
    )

    lines_to_try = [
        re.compile(r"Day\s+(\d+)[^\n]*?(\d{4}-\d{2}-\d{2})[^\n]*", re.IGNORECASE),
    ]

    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    events  = []

    for match in day_pattern.finditer(plan_text):
        day_num   = match.group(1)
        date_str  = match.group(2)
        topics    = match.group(3).strip()
        try:
            dt_start = datetime.strptime(date_str, "%Y-%m-%d")
            dt_end   = dt_start + timedelta(hours=hours_per_day)
            uid      = f"studymind-{subject.lower().replace(' ', '-')}-day{day_num}@studymindai"
            events.append(
                f"BEGIN:VEVENT\r\n"
                f"UID:{uid}\r\n"
                f"DTSTAMP:{now_str}\r\n"
                f"DTSTART:{dt_start.strftime('%Y%m%d')}T090000\r\n"
                f"DTEND:{dt_end.strftime('%Y%m%d')}T{(9+hours_per_day):02d}0000\r\n"
                f"SUMMARY:{subject} — Day {day_num} Study\r\n"
                f"DESCRIPTION:{topics[:200]}\r\n"
                f"END:VEVENT\r\n"
            )
        except ValueError:
            continue

    # If the plan didn't include explicit dates, generate from today
    if not events and plan_result.get("days_left"):
        today = datetime.today().date()
        for i in range(min(int(plan_result["days_left"]), 30)):
            dt    = datetime.combine(today + timedelta(days=i), datetime.min.time())
            dt_end = dt + timedelta(hours=hours_per_day)
            uid   = f"studymind-{subject.lower().replace(' ','-')}-day{i+1}@studymindai"
            events.append(
                f"BEGIN:VEVENT\r\n"
                f"UID:{uid}\r\n"
                f"DTSTAMP:{now_str}\r\n"
                f"DTSTART:{dt.strftime('%Y%m%d')}T090000\r\n"
                f"DTEND:{dt_end.strftime('%Y%m%d')}T{(9+hours_per_day):02d}0000\r\n"
                f"SUMMARY:{subject} — Day {i+1} Study\r\n"
                f"DESCRIPTION:Study session {i+1} for {subject}\r\n"
                f"END:VEVENT\r\n"
            )

    # Exam day reminder
    if exam_date:
        try:
            exam_dt = datetime.strptime(exam_date, "%Y-%m-%d")
            events.append(
                f"BEGIN:VEVENT\r\n"
                f"UID:studymind-exam-{subject.lower().replace(' ','-')}@studymindai\r\n"
                f"DTSTAMP:{now_str}\r\n"
                f"DTSTART:{exam_dt.strftime('%Y%m%d')}\r\n"
                f"DTEND:{exam_dt.strftime('%Y%m%d')}\r\n"
                f"SUMMARY:🎯 {subject} EXAM\r\n"
                f"DESCRIPTION:{subject} exam day\r\n"
                f"END:VEVENT\r\n"
            )
        except ValueError:
            pass

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//StudyMind AI//StudyMind//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        + "".join(events)
        + "END:VCALENDAR\r\n"
    )
    return ics


# ── Multi-subject plan ────────────────────────────────────────────────────────

def generate_multi_subject_plan(subjects_info: list[dict]) -> str:
    """
    Generate a combined weekly schedule for multiple subjects.
    subjects_info = [{"subject": "DBMS", "exam_date": "2025-06-10", "priority": "high"}, ...]
    """
    key = _cache_key(*[f"{s['subject']}{s['exam_date']}{s.get('priority','medium')}" for s in subjects_info])
    with _cache_lock:
        if key in _plan_cache:
            return _plan_cache[key]["plan"]

    subjects_text = "\n".join(
        f"- {s['subject']}: exam on {s['exam_date']}, priority: {s.get('priority', 'medium')}"
        for s in subjects_info
    )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert academic advisor."},
                {"role": "user",   "content": (
                    f"Create a combined weekly study schedule for these subjects:\n{subjects_text}\n\n"
                    "Show a table: Day | Morning | Afternoon | Evening | Total Hours\n"
                    "Balance subjects based on exam dates and priority."
                )},
            ],
            temperature=0.3,
            max_tokens=1200,
            timeout=45,
        )
        result = resp.choices[0].message.content.strip()
    except RateLimitError:
        return "⚠️ Groq rate limit reached. Please wait a moment and try again."
    except APITimeoutError:
        return "⚠️ Request timed out. Please try again."
    except (APIConnectionError, APIError) as e:
        return f"⚠️ API error: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"

    with _cache_lock:
        _plan_cache[key] = {"plan": result}

    return result