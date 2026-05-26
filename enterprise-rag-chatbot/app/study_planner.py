"""
app/study_planner.py
Generates a day-by-day study plan using Groq + syllabus from ChromaDB.
"""

import os
from datetime import datetime, timedelta
from groq import Groq, APIError, RateLimitError, APITimeoutError, APIConnectionError
from retrieval.retriever import retrieve

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


def get_syllabus_topics(subject):
    """Retrieve syllabus topics for a subject from ChromaDB."""
    chunks, _ = retrieve(
        f"syllabus topics units {subject}",
        use_hyde=False,
        use_hybrid=True,
    )
    if not chunks:
        return f"No syllabus found for {subject}. Please upload the syllabus PDF first."
    return "\n".join(c["text"] for c in chunks[:5])


def generate_study_plan(subject, exam_date_str, hours_per_day, difficulty="medium"):
    """
    Generate a structured day-by-day study plan.

    Args:
        subject: Subject name (e.g., "DBMS")
        exam_date_str: Exam date as string "YYYY-MM-DD"
        hours_per_day: Available study hours per day
        difficulty: easy / medium / hard
    """
    today     = datetime.today().date()
    exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    days_left = (exam_date - today).days

    if days_left <= 0:
        return {"error": "Exam date must be in the future."}

    syllabus = get_syllabus_topics(subject)
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
(List each day with: Day N (Date) | Topics | Hours | Focus)

## ⚠️ Priority Topics
(Top 5 most important topics to cover first)

## 💡 Study Tips for {subject}
(3 specific tips for this subject)

## ✅ Revision Plan (Last 2 days)
(What to do in final 2 days before exam)

Be specific and realistic. If days are few, focus on high-priority topics only."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert academic advisor creating personalized study plans."},
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

    return {
        "subject":       subject,
        "exam_date":     exam_date_str,
        "days_left":     days_left,
        "hours_per_day": hours_per_day,
        "total_hours":   total_hours,
        "plan":          plan_text,
    }


def generate_multi_subject_plan(subjects_info):
    """
    Generate a combined plan for multiple subjects.
    subjects_info = [{"subject": "DBMS", "exam_date": "2025-06-10", "priority": "high"}, ...]
    """
    subjects_text = "\n".join(
        f"- {s['subject']}: exam on {s['exam_date']}, priority: {s.get('priority','medium')}"
        for s in subjects_info
    )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert academic advisor."},
                {"role": "user",   "content":
                 f"Create a combined weekly study schedule for these subjects:\n{subjects_text}\n\n"
                 "Show a table: Day | Morning | Afternoon | Evening | Total Hours\n"
                 "Balance subjects based on exam dates and priority."},
            ],
            temperature=0.3,
            max_tokens=1000,
            timeout=45,
        )
        return resp.choices[0].message.content.strip()
    except RateLimitError:
        return "⚠️ Groq rate limit reached. Please wait a moment and try again."
    except APITimeoutError:
        return "⚠️ Request timed out. Please try again."
    except (APIConnectionError, APIError) as e:
        return f"⚠️ API error: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"