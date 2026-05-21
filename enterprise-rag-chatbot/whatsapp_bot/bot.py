"""
whatsapp_bot/bot.py
WhatsApp bot using Twilio sandbox (free).
Run alongside Streamlit: python whatsapp_bot/bot.py
Expose with ngrok: ngrok http 5000
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from app.rag_pipeline import stream_answer

app = Flask(__name__)

# Store conversation history per user (phone number)
user_sessions = {}

WELCOME_MSG = """👋 Welcome to *College Assistant Bot*!

I can answer questions about:
📚 Syllabus & topics
🗓️ Exam schedules
💰 Fee structure
📋 College rules & policies
📝 Previous year questions

Just ask your question!
Type *help* for more commands."""

HELP_MSG = """📖 *Available commands:*

❓ Ask any question about college docs
🔄 *reset* — Clear your chat history
📚 *topics [subject]* — Key topics for a subject
📅 *exam [subject]* — Exam date & syllabus
💡 *tip* — Study tip of the day

_Example: "What is the syllabus for Unit 3 DBMS?"_"""


def get_rag_answer(user_id, query):
    """Get answer from RAG pipeline."""
    history = user_sessions.get(user_id, [])

    # Collect streamed tokens
    full_answer = ""
    sources = []
    for token in stream_answer(
        query=query,
        history=history[-6:],
        use_hyde=True,
        use_hybrid=True,
    ):
        if isinstance(token, dict):
            sources = token.get("sources", [])
        else:
            full_answer += token

    # Update session history
    if user_id not in user_sessions:
        user_sessions[user_id] = []
    user_sessions[user_id].extend([
        {"role": "user",      "content": query},
        {"role": "assistant", "content": full_answer},
    ])

    # Format for WhatsApp
    reply = full_answer
    if sources:
        reply += f"\n\n📎 _Sources: {', '.join(sources)}_"

    return reply[:1500]  # WhatsApp message limit


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming = request.form.get("Body", "").strip()
    sender   = request.form.get("From", "unknown")
    resp     = MessagingResponse()
    msg      = resp.message()

    if not incoming:
        msg.body("Please send a text message.")
        return str(resp)

    lower = incoming.lower()

    if lower in ["hi", "hello", "hey", "start"]:
        msg.body(WELCOME_MSG)

    elif lower == "help":
        msg.body(HELP_MSG)

    elif lower == "reset":
        user_sessions[sender] = []
        msg.body("✅ Chat history cleared! Ask me anything.")

    elif lower == "tip":
        tip = get_rag_answer(sender, "Give me one important study tip for college students")
        msg.body(f"💡 *Study Tip:*\n{tip}")

    elif lower.startswith("topics "):
        subject = incoming[7:].strip()
        answer  = get_rag_answer(sender, f"What are the key topics in {subject}?")
        msg.body(f"📚 *Key topics for {subject}:*\n\n{answer}")

    elif lower.startswith("exam "):
        subject = incoming[5:].strip()
        answer  = get_rag_answer(sender, f"What is the exam schedule and syllabus for {subject}?")
        msg.body(f"🗓️ *{subject} Exam Info:*\n\n{answer}")

    else:
        # Regular RAG query
        msg.body("⏳ Searching documents...\n\n" + get_rag_answer(sender, incoming))

    return str(resp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "bot": "College Assistant WhatsApp Bot"}


if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 College Assistant WhatsApp Bot")
    print("="*50)
    print("Running on http://localhost:5000")
    print("\nNext steps:")
    print("1. Run: ngrok http 5000")
    print("2. Copy the ngrok HTTPS URL")
    print("3. Go to Twilio Console → Messaging → Sandbox")
    print("4. Set webhook URL to: https://YOUR-NGROK-URL/whatsapp")
    print("5. WhatsApp 'join <your-sandbox-word>' to +1 415 523 8886")
    print("="*50 + "\n")
    app.run(debug=False, port=5000)