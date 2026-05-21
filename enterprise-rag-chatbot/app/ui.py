"""
app/ui.py — College Assistant RAG Chatbot
Tabs: Chat | Study Planner | PYQ Analyzer | WhatsApp Setup
"""
import os, sys, tempfile
from pathlib import Path
from datetime import datetime, date
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if not os.environ.get("GROQ_API_KEY"):
    st.error("**GROQ_API_KEY not set.**\n\nIn terminal:\n```\nset GROQ_API_KEY=gsk_your-key\n```")
    st.stop()

from ingestion.ingest import ingest_file, list_ingested_files, get_full_text
from app.rag_pipeline import stream_answer, summarize_document, suggest_followups
from app.study_planner import generate_study_plan, generate_multi_subject_plan
from app.pyq_analyzer import analyze_pyq, compare_pyqs
from app.feedback import log_feedback, feedback_summary

st.set_page_config(page_title="College Assistant", page_icon="🎓",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.source-badge{background:#1e3a5f;color:#a8d4ff;border-radius:4px;
  padding:2px 8px;font-size:0.78rem;margin-right:4px;display:inline-block;}
.warning-box{background:#3d2600;border-left:3px solid #ff9900;
  padding:8px 12px;border-radius:4px;font-size:0.85rem;}
.metric-card{background:#1a1a2e;border-radius:8px;padding:16px;text-align:center;}
</style>""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("messages",[]),("history",[]),("model_ready",False),
             ("pending_query",None),("show_summary",None),
             ("pyq_analyses",[]),("plan_result",None)]:
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.model_ready:
    with st.spinner("⏳ Loading model (first time ~30s)…"):
        try:
            from ingestion.ingest import get_collection
            get_collection()
        except Exception: pass
        st.session_state.model_ready = True

# ── Export helpers ────────────────────────────────────────────────────────────
def export_txt():
    lines = [f"College Assistant — Export {datetime.now().strftime('%Y-%m-%d %H:%M')}\n","="*60]
    for m in st.session_state.messages:
        role = "You" if m["role"]=="user" else "Assistant"
        lines.append(f"\n[{role}]\n{m['content']}")
        if m.get("sources"): lines.append(f"Sources: {', '.join(m['sources'])}")
    return "\n".join(lines)

def export_html():
    rows = ""
    for m in st.session_state.messages:
        color = "#1e3a5f" if m["role"]=="assistant" else "#2d2d2d"
        label = "🤖 Assistant" if m["role"]=="assistant" else "👤 You"
        srcs  = f"<br><small>📎 {' · '.join(m['sources'])}</small>" if m.get("sources") else ""
        rows += f'<div style="margin:12px 0;padding:12px;background:{color};border-radius:8px"><b>{label}</b><br>{m["content"]}{srcs}</div>'
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>Chat Export</title><style>body{{font-family:sans-serif;max-width:860px;margin:auto;padding:20px;background:#111;color:#eee}}</style></head><body><h2>🎓 College Assistant Export</h2><p>{datetime.now().strftime("%Y-%m-%d %H:%M")}</p>{rows}</body></html>'

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 College Assistant")
    st.caption("Powered by Groq + Llama 3")
    st.divider()

    st.header("📁 Upload Documents")
    uploaded_files = st.file_uploader("PDF, DOCX, or TXT",
        type=["pdf","docx","txt"], accept_multiple_files=True)
    doc_type = st.selectbox("Document type",
        ["syllabus","timetable","fees","rules","pyq","general"])

    if uploaded_files:
        if st.button("⚡ Ingest", type="primary", use_container_width=True):
            bar = st.progress(0)
            for i, uf in enumerate(uploaded_files):
                bar.progress((i+1)/len(uploaded_files), text=f"{uf.name}…")
                sfx = Path(uf.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=sfx) as tmp:
                    tmp.write(uf.read()); path = tmp.name
                try:
                    n = ingest_file(path, doc_type=doc_type, original_filename=uf.name)
                    st.success(f"✅ {uf.name} ({n} chunks)")
                except Exception as e:
                    st.error(f"❌ {uf.name}: {e}")
                finally:
                    os.unlink(path)
            bar.empty()
            st.rerun()

    ingested = list_ingested_files()
    if ingested:
        with st.expander(f"📂 Files ({len(ingested)})"):
            for fn in ingested: st.text(f"• {fn}")

    st.divider()
    st.header("⚙️ Settings")
    use_hybrid = st.toggle("Hybrid search", value=True)
    use_hyde   = st.toggle("HyDE rewriting", value=True)
    show_debug = st.toggle("Debug panel",    value=False)
    doc_filter = st.selectbox("Filter by type",
        ["All","syllabus","timetable","fees","rules","pyq","general"])
    active_filter = None if doc_filter=="All" else doc_filter

    st.divider()
    st.header("💾 Export Chat")
    if st.session_state.messages:
        c1,c2 = st.columns(2)
        c1.download_button("📄 TXT", export_txt(),
            f"chat_{datetime.now().strftime('%Y%m%d')}.txt","text/plain",use_container_width=True)
        c2.download_button("🌐 HTML", export_html(),
            f"chat_{datetime.now().strftime('%Y%m%d')}.html","text/html",use_container_width=True)
    else:
        st.caption("No chat yet.")

    st.divider()
    fs = feedback_summary()
    c1,c2 = st.columns(2)
    c1.metric("👍",fs["thumbs_up"]); c2.metric("👎",fs["thumbs_down"])
    if fs["total"]:
        st.progress(fs["approval_rate"]/100, text=f"{fs['approval_rate']}% approval")
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages=[]; st.session_state.history=[]
        st.session_state.plan_result=None; st.rerun()

# ── MAIN TABS ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Chat", "📅 Study Planner", "📊 PYQ Analyzer", "📱 WhatsApp Bot"
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 💬 Ask anything about your college documents")

    if st.session_state.show_summary:
        s = st.session_state.show_summary
        with st.expander(f"📋 Summary: {s['file']}", expanded=True):
            st.markdown(s["text"])
            if st.button("✕ Close"):
                st.session_state.show_summary=None; st.rerun()

    # Summarize button
    if ingested:
        col1, col2 = st.columns([3,1])
        with col2:
            sel = st.selectbox("Summarize doc", ingested, key="sum_sel", label_visibility="collapsed")
            if st.button("📝 Summarize", use_container_width=True):
                with st.spinner(f"Summarizing {sel}…"):
                    txt = get_full_text(sel)
                    if txt:
                        summary = summarize_document(sel, txt)
                        st.session_state.show_summary={"file":sel,"text":summary}
                        st.rerun()

    # Chat messages
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"]=="assistant":
                if msg.get("sources"):
                    badges="".join(f'<span class="source-badge">📎 {s}</span>' for s in msg["sources"])
                    st.markdown(badges, unsafe_allow_html=True)
                if msg.get("warning"):
                    st.markdown(f'<div class="warning-box">⚠️ {msg["warning"]}</div>',unsafe_allow_html=True)
                if show_debug and msg.get("debug"):
                    with st.expander("🔍 Debug"): st.json(msg["debug"])
                if msg.get("followups"):
                    st.markdown("**💡 You might also ask:**")
                    for fq in msg["followups"]:
                        if st.button(f"→ {fq}", key=f"fq_{idx}_{fq[:15]}"):
                            st.session_state.pending_query=fq; st.rerun()
                if not msg.get("rated"):
                    c1,c2,_ = st.columns([1,1,8])
                    if c1.button("👍",key=f"up_{idx}"):
                        log_feedback(msg.get("query",""),msg["content"],msg.get("sources",[]),"up")
                        st.session_state.messages[idx]["rated"]=True; st.rerun()
                    if c2.button("👎",key=f"dn_{idx}"):
                        log_feedback(msg.get("query",""),msg["content"],msg.get("sources",[]),"down")
                        st.session_state.messages[idx]["rated"]=True; st.rerun()

    query = st.chat_input("Ask about syllabus, exams, fees, rules…")
    if st.session_state.pending_query:
        query=st.session_state.pending_query; st.session_state.pending_query=None

    if query:
        st.session_state.messages.append({"role":"user","content":query})
        with st.chat_message("user"): st.markdown(query)
        with st.chat_message("assistant"):
            ph=st.empty(); full=""; meta={}
            for token in stream_answer(query,st.session_state.history,
                                       use_hyde,use_hybrid,active_filter):
                if isinstance(token,dict): meta=token
                else: full+=token; ph.markdown(full+"▌")
            ph.markdown(full)
            srcs=meta.get("sources",[]); grounded=meta.get("grounded",True); warn=None
            if srcs:
                st.markdown("".join(f'<span class="source-badge">📎 {s}</span>' for s in srcs),unsafe_allow_html=True)
            if not grounded:
                warn="Answer may not be fully supported by uploaded documents."
                st.markdown(f'<div class="warning-box">⚠️ {warn}</div>',unsafe_allow_html=True)
            followups=[]
            try:
                with st.spinner(""):
                    followups=suggest_followups(query,full,srcs)
                if followups:
                    st.markdown("**💡 You might also ask:**")
                    for fq in followups:
                        if st.button(f"→ {fq}", key=f"nfq_{fq[:15]}"):
                            st.session_state.pending_query=fq; st.rerun()
            except Exception: pass
            if show_debug:
                with st.expander("🔍 Debug"):
                    st.json({"rewritten":meta.get("rewritten_query"),"chunks":meta.get("chunks_used"),"grounded":grounded})
        st.session_state.messages.append({"role":"assistant","content":full,
            "sources":srcs,"warning":warn,"query":query,"rated":False,"followups":followups,
            "debug":{"rewritten":meta.get("rewritten_query"),"chunks":meta.get("chunks_used"),"grounded":grounded}})
        st.session_state.history+=[{"role":"user","content":query},{"role":"assistant","content":full}]

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — STUDY PLANNER
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📅 Personalized Study Planner")
    st.caption("Generates a day-by-day study schedule based on your syllabus and exam date")

    plan_tab1, plan_tab2 = st.tabs(["Single Subject", "Multiple Subjects"])

    with plan_tab1:
        col1, col2 = st.columns(2)
        with col1:
            subject     = st.text_input("Subject name", placeholder="e.g. DBMS, OS, CN")
            exam_date   = st.date_input("Exam date", min_value=date.today())
            hours_day   = st.slider("Study hours per day", 1, 12, 4)
        with col2:
            difficulty  = st.selectbox("Your current level", ["beginner","medium","advanced"])
            st.markdown("#### 📌 Tips")
            st.info("Upload your syllabus PDF first for a more accurate plan!")

        if st.button("🗓️ Generate Study Plan", type="primary", use_container_width=True):
            if not subject:
                st.warning("Please enter a subject name.")
            else:
                with st.spinner(f"Creating study plan for {subject}…"):
                    result = generate_study_plan(
                        subject, exam_date.strftime("%Y-%m-%d"),
                        hours_day, difficulty)
                st.session_state.plan_result = result

        if st.session_state.plan_result:
            r = st.session_state.plan_result
            if "error" in r:
                st.error(r["error"])
            else:
                col1,col2,col3 = st.columns(3)
                col1.metric("📚 Subject",    r["subject"])
                col2.metric("⏰ Days Left",  r["days_left"])
                col3.metric("🕐 Total Hours",r["total_hours"])
                st.markdown(r["plan"])
                st.download_button("📥 Download Plan",
                    data=r["plan"],
                    file_name=f"study_plan_{r['subject']}_{r['exam_date']}.txt",
                    mime="text/plain")

    with plan_tab2:
        st.markdown("Add multiple subjects and get a combined weekly schedule")
        n_subjects = st.number_input("Number of subjects", 2, 6, 3)
        subjects_info = []
        cols = st.columns(3)
        for i in range(n_subjects):
            with cols[i % 3]:
                st.markdown(f"**Subject {i+1}**")
                sub  = st.text_input("Name",    key=f"ms_{i}", placeholder="DBMS")
                edate= st.date_input("Exam",    key=f"md_{i}", min_value=date.today())
                prio = st.selectbox("Priority", ["high","medium","low"], key=f"mp_{i}")
                if sub:
                    subjects_info.append({"subject":sub,"exam_date":edate.strftime("%Y-%m-%d"),"priority":prio})

        if st.button("📊 Generate Combined Plan", type="primary", use_container_width=True):
            if len(subjects_info) < 2:
                st.warning("Fill in at least 2 subjects.")
            else:
                with st.spinner("Creating combined schedule…"):
                    plan = generate_multi_subject_plan(subjects_info)
                st.markdown(plan)
                st.download_button("📥 Download",data=plan,
                    file_name="combined_study_plan.txt",mime="text/plain")

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — PYQ ANALYZER
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📊 Previous Year Question Analyzer")
    st.caption("Upload PYQ PDFs → get topic frequency, predictions, and study priorities")

    col1, col2 = st.columns([2,1])
    with col1:
        pyq_files   = st.file_uploader("Upload PYQ PDF(s)",
                        type=["pdf"], accept_multiple_files=True, key="pyq_up")
        pyq_subject = st.text_input("Subject name", placeholder="e.g. DBMS")
    with col2:
        st.markdown("#### 💡 How to use")
        st.info("1. Upload 1-3 years of PYQ papers\n2. Enter subject name\n3. Click Analyze\n4. See topic frequency & predictions")

    if st.button("🔍 Analyze PYQs", type="primary", use_container_width=True):
        if not pyq_files or not pyq_subject:
            st.warning("Upload at least one PYQ PDF and enter the subject name.")
        else:
            st.session_state.pyq_analyses = []
            progress = st.progress(0)
            for i, pf in enumerate(pyq_files):
                progress.progress((i+1)/len(pyq_files), text=f"Analyzing {pf.name}…")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pf.read()); path = tmp.name
                try:
                    result = analyze_pyq(path, pyq_subject, original_filename=pf.name)
                    st.session_state.pyq_analyses.append(result)
                except Exception as e:
                    st.error(f"Error analyzing {pf.name}: {e}")
                finally:
                    os.unlink(path)
            progress.empty()

    if st.session_state.pyq_analyses:
        for analysis in st.session_state.pyq_analyses:
            with st.expander(f"📄 {analysis['filename']}", expanded=True):
                col1, col2 = st.columns([3,2])

                with col1:
                    st.markdown(analysis["analysis"])

                with col2:
                    # Topic frequency bar chart
                    if analysis["chart_data"] and len(analysis["chart_data"]) > 1:
                        st.markdown("**📊 Topic Frequency**")
                        import pandas as pd
                        df = pd.DataFrame(
                            list(analysis["chart_data"].items()),
                            columns=["Topic","Questions"])
                        df = df.sort_values("Questions", ascending=False).head(10)
                        st.bar_chart(df.set_index("Topic"))

                    # Predictions
                    if analysis["predictions"]:
                        st.markdown("**🎯 Predicted Topics for Next Exam:**")
                        for j, pred in enumerate(analysis["predictions"], 1):
                            st.markdown(f"{j}. 🔥 {pred}")

        # Multi-year comparison
        if len(st.session_state.pyq_analyses) >= 2:
            st.divider()
            st.markdown("### 📈 Multi-Year Comparison")
            if st.button("🔄 Compare All Years", use_container_width=True):
                with st.spinner("Comparing PYQ patterns across years…"):
                    comparison = compare_pyqs(st.session_state.pyq_analyses)
                st.markdown(comparison)
                st.download_button("📥 Download Analysis",
                    data=comparison, file_name=f"pyq_analysis_{pyq_subject}.txt",
                    mime="text/plain")

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — WHATSAPP SETUP
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 📱 WhatsApp Bot Setup")
    st.caption("Let students ask questions on WhatsApp — no need to open a browser!")

    st.success("🤖 Your WhatsApp bot is ready to deploy! Follow the steps below.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Step 1 — Install dependencies")
        st.code("pip install twilio flask", language="bash")

        st.markdown("#### Step 2 — Get free Twilio account")
        st.markdown("""
1. Go to **[twilio.com](https://twilio.com)** → Sign up free
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. Note your **Account SID** and **Auth Token**
""")

        st.markdown("#### Step 3 — Set credentials")
        st.code("""set TWILIO_ACCOUNT_SID=ACxxxxxx
set TWILIO_AUTH_TOKEN=xxxxxx
set GROQ_API_KEY=gsk_xxxxxx""", language="bash")

    with col2:
        st.markdown("#### Step 4 — Run the bot")
        st.code("python whatsapp_bot/bot.py", language="bash")

        st.markdown("#### Step 5 — Expose with ngrok (free)")
        st.code("""# Install ngrok from ngrok.com
ngrok http 5000""", language="bash")

        st.markdown("#### Step 6 — Connect to Twilio")
        st.markdown("""
1. Copy the ngrok HTTPS URL (e.g. `https://abc123.ngrok.io`)
2. In Twilio Console → Sandbox Settings
3. Set **When a message comes in** to:
   `https://abc123.ngrok.io/whatsapp`
4. Save
""")

    st.divider()
    st.markdown("#### 💬 Test commands students can use")

    commands = {
        "hello / hi": "Get welcome message",
        "help": "See all commands",
        "topics DBMS": "Get key topics for DBMS",
        "exam OS": "Get OS exam info",
        "tip": "Get a study tip",
        "reset": "Clear chat history",
        "Any question": "Get RAG answer from your documents",
    }

    col1, col2 = st.columns(2)
    for i, (cmd, desc) in enumerate(commands.items()):
        target = col1 if i % 2 == 0 else col2
        target.markdown(f"**`{cmd}`** — {desc}")

    st.divider()
    st.info("💡 **Pro tip for your placement interview:** Say you deployed a WhatsApp bot using Twilio + Flask + RAG pipeline that lets college students query institutional documents in natural language over WhatsApp — zero learning curve for end users!")