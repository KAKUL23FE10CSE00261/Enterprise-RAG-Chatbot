"""
app/ui.py — College Assistant RAG Chatbot
Redesigned: Login system, chat history, onboarding, delete docs, beautiful aesthetic
"""
import os, sys, tempfile, json, hashlib, time
from pathlib import Path
from datetime import datetime, date
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Page config (must be first) ───────────────────────────────────────────────
st.set_page_config(
    page_title="StudyMind AI",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Full CSS theme ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Root variables ── */
:root {
  --blush:    #f5c6d0;
  --rose:     #e8829a;
  --deep:     #c45c78;
  --mauve:    #b784a7;
  --lavender: #d4b8e0;
  --cream:    #fdf6f0;
  --warm:     #fef3e8;
  --text:     #3d2c35;
  --muted:    #8c7080;
  --surface:  #ffffff;
  --border:   #f0dde6;
  --shadow:   0 4px 24px rgba(196,92,120,0.10);
  --shadow-lg:0 8px 40px rgba(196,92,120,0.16);
}

/* ── Global reset ── */
* { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
  background: linear-gradient(135deg, #fdf6f0 0%, #fdf0f5 50%, #f5f0fd 100%) !important;
  font-family: 'DM Sans', sans-serif !important;
  color: var(--text) !important;
}

/* Hide default Streamlit elements */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--cream); }
::-webkit-scrollbar-thumb { background: var(--blush); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--rose); }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #fff5f8 0%, #fdf0f8 100%) !important;
  border-right: 1.5px solid var(--border) !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ── Main content padding ── */
.main .block-container {
  padding: 1.5rem 2rem 2rem !important;
  max-width: 1100px !important;
}

/* ── Cards ── */
.card {
  background: white;
  border-radius: 20px;
  padding: 24px 28px;
  border: 1.5px solid var(--border);
  box-shadow: var(--shadow);
  margin-bottom: 16px;
  transition: box-shadow 0.2s;
}
.card:hover { box-shadow: var(--shadow-lg); }

/* ── Header area ── */
.app-header {
  background: linear-gradient(135deg, #fff0f5 0%, #f8f0ff 100%);
  border-radius: 24px;
  padding: 28px 32px;
  margin-bottom: 24px;
  border: 1.5px solid var(--border);
  display: flex;
  align-items: center;
  gap: 16px;
}
.app-header h1 {
  font-family: 'Playfair Display', serif !important;
  font-size: 2rem !important;
  font-weight: 700 !important;
  color: var(--deep) !important;
  margin: 0 !important;
  line-height: 1.2 !important;
}
.app-header p {
  color: var(--muted) !important;
  margin: 4px 0 0 !important;
  font-size: 0.92rem !important;
}

/* ── Login card ── */
.login-wrap {
  max-width: 440px;
  margin: 60px auto 0;
}
.login-logo {
  text-align: center;
  margin-bottom: 24px;
}
.login-logo h1 {
  font-family: 'Playfair Display', serif;
  font-size: 2.4rem;
  color: var(--deep);
  margin: 8px 0 4px;
}
.login-logo p { color: var(--muted); font-size: 0.92rem; }

/* ── Chat bubbles ── */
.chat-bubble-user {
  background: linear-gradient(135deg, var(--rose) 0%, var(--deep) 100%);
  color: white;
  border-radius: 20px 20px 4px 20px;
  padding: 14px 18px;
  margin: 8px 0 8px 20%;
  font-size: 0.92rem;
  line-height: 1.55;
  box-shadow: 0 3px 16px rgba(196,92,120,0.25);
}
.chat-bubble-ai {
  background: white;
  color: var(--text);
  border-radius: 20px 20px 20px 4px;
  padding: 14px 18px;
  margin: 8px 20% 8px 0;
  font-size: 0.92rem;
  line-height: 1.6;
  border: 1.5px solid var(--border);
  box-shadow: 0 3px 12px rgba(196,92,120,0.08);
}
.chat-meta {
  font-size: 0.72rem;
  color: var(--muted);
  margin-top: 4px;
  text-align: right;
}
.chat-meta-left { text-align: left; }

/* ── Source badge ── */
.source-badge {
  background: linear-gradient(135deg, #fdf0f5, #f5eaff);
  color: var(--deep);
  border: 1px solid var(--blush);
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 0.72rem;
  margin-right: 5px;
  display: inline-block;
  margin-top: 6px;
}

/* ── Warning box ── */
.warning-box {
  background: linear-gradient(135deg, #fff8e8, #fff3e0);
  border-left: 3px solid #f0a500;
  padding: 10px 14px;
  border-radius: 0 10px 10px 0;
  font-size: 0.82rem;
  color: #7a5200;
  margin-top: 8px;
}

/* ── Onboarding empty state ── */
.onboard-wrap {
  text-align: center;
  padding: 48px 24px;
}
.onboard-wrap h2 {
  font-family: 'Playfair Display', serif;
  color: var(--deep);
  font-size: 1.7rem;
  margin-bottom: 8px;
}
.onboard-wrap p { color: var(--muted); margin-bottom: 28px; }
.sample-q {
  background: white;
  border: 1.5px solid var(--border);
  border-radius: 14px;
  padding: 12px 18px;
  margin: 6px auto;
  max-width: 480px;
  cursor: pointer;
  transition: all 0.18s;
  text-align: left;
  font-size: 0.88rem;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 10px;
}
.sample-q:hover {
  border-color: var(--rose);
  box-shadow: 0 4px 16px rgba(196,92,120,0.15);
  transform: translateY(-1px);
}

/* ── File pills ── */
.file-pill {
  background: white;
  border: 1.5px solid var(--border);
  border-radius: 30px;
  padding: 6px 14px;
  font-size: 0.80rem;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 3px;
  color: var(--text);
}

/* ── Sidebar logo ── */
.sidebar-logo {
  background: linear-gradient(135deg, var(--rose), var(--mauve));
  border-radius: 0 0 24px 24px;
  padding: 20px 16px 18px;
  text-align: center;
  margin: -1rem -1rem 20px;
}
.sidebar-logo h2 {
  font-family: 'Playfair Display', serif;
  color: white;
  margin: 0;
  font-size: 1.3rem;
  letter-spacing: 0.5px;
}
.sidebar-logo p { color: rgba(255,255,255,0.8); font-size: 0.75rem; margin: 2px 0 0; }

/* ── User pill in sidebar ── */
.user-pill {
  background: white;
  border: 1.5px solid var(--border);
  border-radius: 14px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.user-avatar {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--rose), var(--mauve));
  display: flex; align-items: center; justify-content: center;
  color: white; font-weight: 600; font-size: 0.9rem;
  flex-shrink: 0;
}

/* ── Tabs override ── */
[data-testid="stTabs"] [role="tablist"] {
  background: white;
  border-radius: 14px;
  padding: 4px;
  border: 1.5px solid var(--border);
  gap: 2px;
  margin-bottom: 20px;
}
[data-testid="stTabs"] [role="tab"] {
  border-radius: 10px !important;
  padding: 8px 18px !important;
  font-size: 0.86rem !important;
  font-weight: 500 !important;
  color: var(--muted) !important;
  border: none !important;
  transition: all 0.18s !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, var(--rose), var(--deep)) !important;
  color: white !important;
  box-shadow: 0 2px 10px rgba(196,92,120,0.30) !important;
}

/* ── Input styling ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stChatInput"] textarea {
  border-radius: 12px !important;
  border: 1.5px solid var(--border) !important;
  background: white !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.88rem !important;
  color: var(--text) !important;
  transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--rose) !important;
  box-shadow: 0 0 0 3px rgba(232,130,154,0.15) !important;
}
[data-testid="stChatInput"] {
  border-radius: 16px !important;
  border: 1.5px solid var(--border) !important;
  background: white !important;
  box-shadow: var(--shadow) !important;
}

/* ── Buttons ── */
[data-testid="stButton"] button {
  border-radius: 12px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 500 !important;
  font-size: 0.86rem !important;
  transition: all 0.18s !important;
  border: 1.5px solid transparent !important;
}
[data-testid="stButton"] button[kind="primary"] {
  background: linear-gradient(135deg, var(--rose), var(--deep)) !important;
  color: white !important;
  box-shadow: 0 3px 12px rgba(196,92,120,0.30) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 5px 18px rgba(196,92,120,0.40) !important;
}
[data-testid="stButton"] button[kind="secondary"] {
  background: white !important;
  color: var(--deep) !important;
  border-color: var(--blush) !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
  background: var(--cream) !important;
  border-color: var(--rose) !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
  background: white !important;
  border-radius: 16px !important;
  padding: 16px 20px !important;
  border: 1.5px solid var(--border) !important;
  box-shadow: var(--shadow) !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
  font-size: 0.78rem !important;
  color: var(--muted) !important;
  font-weight: 500 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  font-family: 'Playfair Display', serif !important;
  color: var(--deep) !important;
  font-size: 1.6rem !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
  border-radius: 14px !important;
  border: 1.5px solid var(--border) !important;
  background: white !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary {
  font-weight: 500 !important;
  color: var(--text) !important;
  padding: 12px 16px !important;
}

/* ── Select boxes ── */
[data-testid="stSelectbox"] > div > div {
  border-radius: 12px !important;
  border: 1.5px solid var(--border) !important;
  background: white !important;
}

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, var(--rose), var(--mauve)) !important;
  border-radius: 4px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
  border-radius: 14px !important;
  border: none !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
  background: white !important;
  color: var(--deep) !important;
  border: 1.5px solid var(--blush) !important;
  border-radius: 12px !important;
}

/* ── Chat history list ── */
.hist-item {
  padding: 10px 14px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.16s;
  border: 1.5px solid transparent;
  margin-bottom: 4px;
  font-size: 0.82rem;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hist-item:hover { background: white; border-color: var(--border); }
.hist-item.active {
  background: linear-gradient(135deg, #fff0f5, #f5eaff);
  border-color: var(--blush);
  color: var(--deep);
  font-weight: 500;
}

/* ── Divider ── */
hr {
  border: none !important;
  border-top: 1.5px solid var(--border) !important;
  margin: 16px 0 !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] { color: var(--rose) !important; }

/* ── Toggle ── */
[data-testid="stToggle"] { accent-color: var(--rose) !important; }

/* ── Slider ── */
[data-testid="stSlider"] [role="slider"] { background: var(--rose) !important; }

/* ── Grounded badges ── */
.grounded-badge {
  display: inline-block;
  background: #e8f8ef; color: #1a7a45;
  border: 1px solid #a8dfc0; border-radius: 20px;
  padding: 2px 10px; font-size: 0.72rem; margin-left: 6px;
}
.ungrounded-badge {
  display: inline-block;
  background: #fff3e0; color: #8a5200;
  border: 1px solid #ffd080; border-radius: 20px;
  padding: 2px 10px; font-size: 0.72rem; margin-left: 6px;
}

/* ── PYQ section titles ── */
.pyq-section-title {
  font-family: 'Playfair Display', serif;
  color: var(--deep); font-size: 1rem; font-weight: 600;
  margin: 16px 0 8px; padding-bottom: 6px;
  border-bottom: 2px solid var(--blush);
}

/* ── Animate chat messages ── */
@keyframes slideIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.chat-bubble-user, .chat-bubble-ai { animation: slideIn 0.25s ease; }
</style>
""", unsafe_allow_html=True)


# ── Auth helpers ──────────────────────────────────────────────────────────────

USERS_FILE = Path(__file__).parent.parent / "data" / "users.json"

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> dict:
    USERS_FILE.parent.mkdir(exist_ok=True)
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    users = {"admin": {"password": hash_pw("admin123"), "name": "Admin",
                       "created": datetime.utcnow().isoformat()}}
    USERS_FILE.write_text(json.dumps(users, indent=2))
    return users

def save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2))

def register_user(username: str, password: str, name: str) -> tuple[bool, str]:
    users = load_users()
    if username in users:
        return False, "Username already exists"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    users[username] = {"password": hash_pw(password), "name": name,
                       "created": datetime.utcnow().isoformat()}
    save_users(users)
    return True, "Account created!"

def authenticate(username: str, password: str) -> tuple[bool, str]:
    users = load_users()
    if username not in users:
        return False, "User not found"
    if users[username]["password"] != hash_pw(password):
        return False, "Incorrect password"
    return True, users[username]["name"]


# ── Chat history persistence ──────────────────────────────────────────────────

HISTORY_DIR = Path(__file__).parent.parent / "data" / "chat_history"

def get_user_history_dir(username: str) -> Path:
    d = HISTORY_DIR / username
    d.mkdir(parents=True, exist_ok=True)
    return d

def list_chat_sessions(username: str) -> list[dict]:
    d = get_user_history_dir(username)
    sessions = []
    for f in sorted(d.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            sessions.append({"id": f.stem, "title": data.get("title", "New Chat"),
                              "created": data.get("created", ""),
                              "messages": data.get("messages", [])})
        except Exception:
            pass
    return sessions

def save_chat_session(username: str, session_id: str, title: str, messages: list):
    d = get_user_history_dir(username)
    path = d / f"{session_id}.json"
    path.write_text(json.dumps({"id": session_id, "title": title,
                                 "created": datetime.utcnow().isoformat(),
                                 "messages": messages},
                                indent=2, ensure_ascii=False))

def delete_chat_session(username: str, session_id: str):
    d = get_user_history_dir(username)
    p = d / f"{session_id}.json"
    if p.exists():
        p.unlink()

def new_session_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_") + str(int(time.time() * 1000))[-4:]


# ── Session state init ────────────────────────────────────────────────────────
defaults = {
    "logged_in": False, "username": None, "user_name": None,
    "auth_page": "login",
    "messages": [], "history": [], "model_ready": False,
    "current_session_id": None, "current_session_title": "New Chat",
    "pending_query": None, "show_summary": None,
    "pyq_analyses": [], "plan_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════════════════════════════════
# AUTH WALL
# ════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("""
        <div class='login-logo'>
          <div style='font-size:3.2rem;'>🌸</div>
          <h1>StudyMind AI</h1>
          <p>Your intelligent college document assistant</p>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.auth_page == "login":
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("**Welcome back ✨**")
            st.caption("Sign in to continue your learning journey")
            st.markdown("<br>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="your username", key="li_user")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="li_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Sign In →", type="primary", use_container_width=True):
                if username and password:
                    ok, msg = authenticate(username, password)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.username  = username
                        st.session_state.user_name = msg
                        st.session_state.current_session_id = new_session_id()
                        st.rerun()
                    else:
                        st.error(f"🌺 {msg}")
                else:
                    st.warning("Please fill in both fields")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;font-size:0.85rem;color:#8c7080;'>Don't have an account?</div>",
                        unsafe_allow_html=True)
            if st.button("Create Account 🌷", use_container_width=True):
                st.session_state.auth_page = "register"
                st.rerun()

        else:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("**Create your account 🌷**")
            st.caption("Join to start chatting with your documents")
            st.markdown("<br>", unsafe_allow_html=True)
            r_name  = st.text_input("Your name", placeholder="e.g. Kakul", key="reg_name")
            r_user  = st.text_input("Choose username", placeholder="unique username", key="reg_user")
            r_pass  = st.text_input("Password (min 6 chars)", type="password",
                                    placeholder="••••••••", key="reg_pass")
            r_pass2 = st.text_input("Confirm password", type="password",
                                    placeholder="••••••••", key="reg_pass2")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create Account →", type="primary", use_container_width=True):
                if r_pass != r_pass2:
                    st.error("Passwords don't match 🌺")
                elif r_name and r_user and r_pass:
                    ok, msg = register_user(r_user, r_pass, r_name)
                    if ok:
                        st.success(f"✅ {msg} Please sign in.")
                        st.session_state.auth_page = "login"
                        st.rerun()
                    else:
                        st.error(f"🌺 {msg}")
                else:
                    st.warning("Please fill all fields")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("← Back to Sign In", use_container_width=True):
                st.session_state.auth_page = "login"
                st.rerun()

    st.stop()


# ── Post-login checks ─────────────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    st.error("**GROQ_API_KEY not set.** In terminal: `set GROQ_API_KEY=gsk_your-key`")
    st.stop()

from ingestion.ingest import ingest_file, list_ingested_files, get_full_text, delete_file
from app.rag_pipeline import stream_answer, summarize_document, suggest_followups
from app.study_planner import generate_study_plan, generate_multi_subject_plan
from app.pyq_analyzer import analyze_pyq, compare_pyqs
from app.feedback import log_feedback, feedback_summary

if not st.session_state.model_ready:
    with st.spinner("🌸 Loading AI model (first time ~30s)…"):
        try:
            from ingestion.ingest import get_collection
            get_collection()
        except Exception:
            pass
        st.session_state.model_ready = True


# ── Export helpers ────────────────────────────────────────────────────────────
def export_txt():
    lines = [f"StudyMind AI — {st.session_state.current_session_title}\n"
             f"Exported {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'='*60}"]
    for m in st.session_state.messages:
        role = "You" if m["role"] == "user" else "Assistant"
        lines.append(f"\n[{role}]\n{m['content']}")
        if m.get("sources"):
            lines.append(f"Sources: {', '.join(m['sources'])}")
    return "\n".join(lines)

def export_html():
    rows = ""
    for m in st.session_state.messages:
        if m["role"] == "user":
            rows += (f'<div style="margin:10px 0 10px 20%;background:linear-gradient(135deg,#e8829a,#c45c78);'
                     f'color:white;border-radius:18px 18px 4px 18px;padding:12px 16px;font-size:0.88rem">'
                     f'{m["content"]}</div>')
        else:
            src = "".join(
                f'<span style="background:#fdf0f5;color:#c45c78;border:1px solid #f5c6d0;'
                f'border-radius:12px;padding:2px 8px;font-size:0.70rem;margin-right:4px">📎 {s}</span>'
                for s in m.get("sources", []))
            rows += (f'<div style="margin:10px 20% 10px 0;background:white;border:1.5px solid #f0dde6;'
                     f'border-radius:18px 18px 18px 4px;padding:12px 16px;font-size:0.88rem">'
                     f'{m["content"]}{("<br><br>" + src) if src else ""}</div>')
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<title>{st.session_state.current_session_title}</title>'
            f'<style>body{{font-family:"DM Sans",sans-serif;max-width:820px;margin:auto;'
            f'padding:24px;background:#fdf6f0;color:#3d2c35}}'
            f'h2{{font-family:"Playfair Display",serif;color:#c45c78}}</style>'
            f'<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700'
            f'&family=DM+Sans&display=swap" rel="stylesheet"></head><body>'
            f'<h2>🌸 {st.session_state.current_session_title}</h2>'
            f'<p style="color:#8c7080;font-size:0.82rem">'
            f'{datetime.now().strftime("%Y-%m-%d %H:%M")} · {st.session_state.user_name}</p>'
            f'{rows}</body></html>')


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class='sidebar-logo'>
      <div style='font-size:1.6rem;margin-bottom:4px;'>🌸</div>
      <h2>StudyMind AI</h2>
      <p>Powered by Groq + Llama 3</p>
    </div>
    """, unsafe_allow_html=True)

    initials = "".join(w[0].upper() for w in st.session_state.user_name.split()[:2])
    st.markdown(f"""
    <div class='user-pill'>
      <div class='user-avatar'>{initials}</div>
      <div>
        <div style='font-weight:600;font-size:0.86rem;color:#3d2c35;'>{st.session_state.user_name}</div>
        <div style='font-size:0.72rem;color:#8c7080;'>@{st.session_state.username}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Chat History ──────────────────────────────────────────────────────
    with st.expander("💬 Chat History", expanded=True):
        if st.button("＋ New Chat", use_container_width=True, type="primary"):
            if st.session_state.messages:
                save_chat_session(st.session_state.username,
                                  st.session_state.current_session_id,
                                  st.session_state.current_session_title,
                                  st.session_state.messages)
            st.session_state.messages = []
            st.session_state.history  = []
            st.session_state.current_session_id    = new_session_id()
            st.session_state.current_session_title = "New Chat"
            st.session_state.show_summary = None
            st.rerun()

        sessions = list_chat_sessions(st.session_state.username)
        if sessions:
            for sess in sessions[:20]:
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    label = f"💬 {sess['title'][:28]}{'…' if len(sess['title']) > 28 else ''}"
                    if st.button(label, key=f"sess_{sess['id']}", use_container_width=True):
                        if st.session_state.messages:
                            save_chat_session(st.session_state.username,
                                              st.session_state.current_session_id,
                                              st.session_state.current_session_title,
                                              st.session_state.messages)
                        st.session_state.messages = sess["messages"]
                        st.session_state.history  = [{"role": m["role"], "content": m["content"]}
                                                      for m in sess["messages"]]
                        st.session_state.current_session_id    = sess["id"]
                        st.session_state.current_session_title = sess["title"]
                        st.rerun()
                with col_b:
                    if st.button("🗑", key=f"del_sess_{sess['id']}"):
                        delete_chat_session(st.session_state.username, sess["id"])
                        if sess["id"] == st.session_state.current_session_id:
                            st.session_state.messages = []
                            st.session_state.history  = []
                            st.session_state.current_session_id    = new_session_id()
                            st.session_state.current_session_title = "New Chat"
                        st.rerun()
        else:
            st.caption("No chat history yet 🌸")

    # ── Documents ─────────────────────────────────────────────────────────
    with st.expander("📁 Documents", expanded=False):
        uploaded_files = st.file_uploader("Upload PDF, DOCX, or TXT",
            type=["pdf", "docx", "txt"], accept_multiple_files=True,
            label_visibility="collapsed")
        doc_type = st.selectbox("Type",
            ["syllabus", "timetable", "fees", "rules", "pyq", "general"],
            label_visibility="collapsed")

        if uploaded_files:
            if st.button("⚡ Ingest", type="primary", use_container_width=True):
                bar = st.progress(0)
                for i, uf in enumerate(uploaded_files):
                    bar.progress((i + 1) / len(uploaded_files), text=f"{uf.name}…")
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
            st.markdown(f"<div style='font-size:0.75rem;color:#8c7080;margin:8px 0 4px;'>"
                        f"📂 {len(ingested)} file(s) ingested</div>", unsafe_allow_html=True)
            for fn in ingested:
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"<div class='file-pill'>📄 {fn[:24]}{'…' if len(fn) > 24 else ''}</div>",
                                unsafe_allow_html=True)
                with c2:
                    if st.button("✕", key=f"del_{fn}", help=f"Remove {fn}"):
                        try:
                            delete_file(fn)
                            st.success(f"Removed {fn}")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        else:
            st.caption("No documents yet")

    # ── Settings ──────────────────────────────────────────────────────────
    with st.expander("⚙️ Settings", expanded=False):
        use_hybrid = st.toggle("Hybrid search",  value=True)
        use_hyde   = st.toggle("HyDE rewriting",  value=True)
        show_debug = st.toggle("Debug panel",     value=False)
        doc_filter = st.selectbox("Filter by doc type",
            ["All", "syllabus", "timetable", "fees", "rules", "pyq", "general"])
        active_filter = None if doc_filter == "All" else doc_filter

    # ── Export ────────────────────────────────────────────────────────────
    with st.expander("💾 Export Chat", expanded=False):
        if st.session_state.messages:
            c1, c2 = st.columns(2)
            c1.download_button("📄 TXT", export_txt(),
                f"chat_{datetime.now().strftime('%Y%m%d')}.txt", "text/plain",
                use_container_width=True)
            c2.download_button("🌐 HTML", export_html(),
                f"chat_{datetime.now().strftime('%Y%m%d')}.html", "text/html",
                use_container_width=True)
        else:
            st.caption("No chat to export yet")

    # ── Feedback Stats ────────────────────────────────────────────────────
    with st.expander("📊 Feedback Stats", expanded=False):
        fs = feedback_summary()
        c1, c2 = st.columns(2)
        c1.metric("👍 Helpful", fs["thumbs_up"])
        c2.metric("👎 Not helpful", fs["thumbs_down"])
        if fs["total"]:
            st.progress(fs["approval_rate"] / 100,
                        text=f"{fs['approval_rate']}% approval rate")

    st.divider()
    if st.button("🚪 Sign Out", use_container_width=True):
        if st.session_state.messages:
            save_chat_session(st.session_state.username,
                              st.session_state.current_session_id,
                              st.session_state.current_session_title,
                              st.session_state.messages)
        for k in list(defaults.keys()):
            del st.session_state[k]
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# MAIN HEADER
# ════════════════════════════════════════════════════════════════════════════
ingested = list_ingested_files()

st.markdown(f"""
<div class='app-header'>
  <div style='font-size:2.6rem;'>🌸</div>
  <div>
    <h1>StudyMind AI</h1>
    <p>Hello, {st.session_state.user_name}! ·
       {len(ingested)} document{'s' if len(ingested) != 1 else ''} ready ·
       {st.session_state.current_session_title}</p>
  </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📅 Study Planner", "📊 PYQ Analyzer"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    if not ingested and not st.session_state.messages:
        st.markdown("""
        <div class='onboard-wrap'>
          <div style='font-size:3rem;margin-bottom:12px;'>📚</div>
          <h2>Upload your first document</h2>
          <p>Add PDFs, DOCX, or TXT files in the sidebar to start chatting with your study materials</p>
        </div>
        """, unsafe_allow_html=True)
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            st.markdown("**💡 Once uploaded, you can ask things like:**")
            for icon, q in [("📖", "What are the main topics in the syllabus?"),
                             ("📋", "Summarize the academic rules for attendance"),
                             ("🗓️", "What are the examination guidelines?"),
                             ("💡", "Explain the grading system")]:
                st.markdown(f"<div class='sample-q'><span style='font-size:1.1rem;'>{icon}</span>"
                            f"<span>{q}</span></div>", unsafe_allow_html=True)
    else:
        if ingested:
            if st.session_state.show_summary:
                s = st.session_state.show_summary
                with st.expander(f"📋 Summary: {s['file']}", expanded=True):
                    st.markdown(s["text"])
                    if st.button("✕ Close summary"):
                        st.session_state.show_summary = None
                        st.rerun()

            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                sel = st.selectbox("", ingested, key="sum_sel", label_visibility="collapsed")
            with col_btn:
                if st.button("📝 Summarize", use_container_width=True):
                    with st.spinner(f"Summarizing {sel}…"):
                        txt = get_full_text(sel)
                        if txt:
                            st.session_state.show_summary = {
                                "file": sel, "text": summarize_document(sel, txt)}
                            st.rerun()

        if not st.session_state.messages:
            st.markdown("""
            <div style='text-align:center;padding:32px 0;color:#8c7080;font-size:0.9rem;'>
              <div style='font-size:2rem;margin-bottom:8px;'>💬</div>
              Ask me anything about your uploaded documents!
            </div>
            """, unsafe_allow_html=True)

        for idx, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>"
                            f"<div class='chat-meta'>{msg.get('time', '')}</div>",
                            unsafe_allow_html=True)
            else:
                g_html = ("<span class='grounded-badge'>✓ Grounded</span>"
                          if msg.get("grounded") else
                          "<span class='ungrounded-badge'>⚠ Verify</span>"
                          if "grounded" in msg else "")
                badges = "".join(f"<span class='source-badge'>📎 {s}</span>"
                                 for s in msg.get("sources", []))
                st.markdown(
                    f"<div class='chat-bubble-ai'>{msg['content']}"
                    f"<div style='margin-top:10px;border-top:1px solid #f0dde6;padding-top:8px;'>"
                    f"{badges}{g_html}</div></div>"
                    f"<div class='chat-meta chat-meta-left'>{msg.get('time', '')}</div>",
                    unsafe_allow_html=True)

                if msg.get("warning"):
                    st.markdown(f'<div class="warning-box">⚠️ {msg["warning"]}</div>',
                                unsafe_allow_html=True)
                if show_debug and msg.get("debug"):
                    with st.expander("🔍 Debug info"):
                        st.json(msg["debug"])
                if msg.get("followups"):
                    st.markdown("<div style='margin:8px 0 4px;font-size:0.78rem;color:#8c7080;'>"
                                "💡 You might also ask:</div>", unsafe_allow_html=True)
                    for fq in msg["followups"]:
                        if st.button(f"→ {fq}", key=f"fq_{idx}_{fq[:12]}"):
                            st.session_state.pending_query = fq
                            st.rerun()
                if not msg.get("rated"):
                    c1, c2, _ = st.columns([1, 1, 8])
                    if c1.button("👍", key=f"up_{idx}"):
                        log_feedback(msg.get("query", ""), msg["content"],
                                     msg.get("sources", []), "up")
                        st.session_state.messages[idx]["rated"] = True
                        st.rerun()
                    if c2.button("👎", key=f"dn_{idx}"):
                        log_feedback(msg.get("query", ""), msg["content"],
                                     msg.get("sources", []), "down")
                        st.session_state.messages[idx]["rated"] = True
                        st.rerun()

        query = st.chat_input("Ask about your syllabus, exams, fees, rules…")
        if st.session_state.pending_query:
            query = st.session_state.pending_query
            st.session_state.pending_query = None

        if query:
            if not st.session_state.messages:
                st.session_state.current_session_title = query[:40] + ("…" if len(query) > 40 else "")
            now = datetime.now().strftime("%H:%M")
            st.session_state.messages.append({"role": "user", "content": query, "time": now})
            st.markdown(f"<div class='chat-bubble-user'>{query}</div>"
                        f"<div class='chat-meta'>{now}</div>", unsafe_allow_html=True)

            with st.spinner("🌸 Thinking…"):
                full = ""; meta = {}
                ph = st.empty()
                for token in stream_answer(query, st.session_state.history,
                                           use_hyde, use_hybrid, active_filter):
                    if isinstance(token, dict):
                        meta = token
                    else:
                        full += token
                        ph.markdown(f'<div class="chat-bubble-ai">{full}▌</div>',
                                    unsafe_allow_html=True)
                ph.empty()

            srcs     = meta.get("sources", [])
            grounded = meta.get("grounded", True)
            warn     = None if grounded else "Answer may not be fully supported by documents."
            followups = []
            try:
                followups = suggest_followups(query, full, srcs)
            except Exception:
                pass

            st.session_state.messages.append({
                "role": "assistant", "content": full,
                "sources": srcs, "grounded": grounded, "warning": warn,
                "query": query, "rated": False, "followups": followups, "time": now,
                "debug": {"rewritten": meta.get("rewritten_query"),
                          "chunks": meta.get("chunks_used"), "grounded": grounded},
            })
            st.session_state.history += [{"role": "user", "content": query},
                                          {"role": "assistant", "content": full}]
            save_chat_session(st.session_state.username,
                              st.session_state.current_session_id,
                              st.session_state.current_session_title,
                              st.session_state.messages)
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — STUDY PLANNER
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div class='card' style='background:linear-gradient(135deg,#fff0f5,#f5eaff);'>
      <div style='display:flex;align-items:center;gap:12px;'>
        <div style='font-size:2rem;'>📅</div>
        <div>
          <div style='font-family:"Playfair Display",serif;font-size:1.2rem;color:#c45c78;font-weight:600;'>
            Personalized Study Planner</div>
          <div style='font-size:0.82rem;color:#8c7080;margin-top:2px;'>
            Generate a day-by-day schedule based on your syllabus and exam date</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    plan_tab1, plan_tab2 = st.tabs(["📖 Single Subject", "📚 Multiple Subjects"])

    with plan_tab1:
        col1, col2 = st.columns(2)
        with col1:
            subject   = st.text_input("Subject name", placeholder="e.g. DBMS, OS, CN")
            exam_date = st.date_input("Exam date", min_value=date.today())
            hours_day = st.slider("Study hours per day", 1, 12, 4)
        with col2:
            difficulty = st.selectbox("Your current level",
                ["beginner", "medium", "advanced"],
                format_func=lambda x: {"beginner": "🌱 Beginner",
                                        "medium": "🌿 Medium",
                                        "advanced": "🌳 Advanced"}[x])
            st.markdown("""
            <div style='background:linear-gradient(135deg,#fff0f5,#f5eaff);border-radius:14px;
                        padding:14px 16px;border:1.5px solid #f0dde6;font-size:0.82rem;color:#3d2c35;'>
              <strong>💡 Pro tip:</strong> Upload your syllabus PDF first for a more accurate plan!
            </div>
            """, unsafe_allow_html=True)

        if st.button("🗓️ Generate Study Plan", type="primary", use_container_width=True):
            if not subject:
                st.warning("Please enter a subject name 🌸")
            else:
                with st.spinner(f"Creating your plan for {subject}…"):
                    result = generate_study_plan(subject, exam_date.strftime("%Y-%m-%d"),
                                                  hours_day, difficulty)
                st.session_state.plan_result = result

        if st.session_state.plan_result:
            r = st.session_state.plan_result
            if "error" in r:
                st.error(r["error"])
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("📚 Subject",    r["subject"])
                c2.metric("⏰ Days Left",  r["days_left"])
                c3.metric("🕐 Total Hours", r["total_hours"])
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f'<div class="card">{r["plan"]}</div>', unsafe_allow_html=True)
                st.download_button("📥 Download Plan", data=r["plan"],
                    file_name=f"study_plan_{r['subject']}_{r['exam_date']}.txt",
                    mime="text/plain", use_container_width=True)

    with plan_tab2:
        st.markdown("<div style='font-size:0.86rem;color:#8c7080;margin-bottom:16px;'>"
                    "Add multiple subjects and get a combined weekly schedule 📚</div>",
                    unsafe_allow_html=True)
        n_subjects = st.number_input("Number of subjects", 2, 6, 3)
        subjects_info = []
        cols = st.columns(3)
        for i in range(n_subjects):
            with cols[i % 3]:
                st.markdown(f"<div style='font-weight:600;font-size:0.85rem;color:#c45c78;"
                            f"margin-bottom:6px;'>Subject {i+1}</div>", unsafe_allow_html=True)
                sub   = st.text_input("Name",     key=f"ms_{i}", placeholder="DBMS")
                edate = st.date_input("Exam date", key=f"md_{i}", min_value=date.today())
                prio  = st.selectbox("Priority",  ["high", "medium", "low"], key=f"mp_{i}",
                    format_func=lambda x: {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}[x])
                if sub:
                    subjects_info.append({"subject": sub,
                                          "exam_date": edate.strftime("%Y-%m-%d"),
                                          "priority": prio})

        if st.button("📊 Generate Combined Plan", type="primary", use_container_width=True):
            if len(subjects_info) < 2:
                st.warning("Fill in at least 2 subjects 🌸")
            else:
                with st.spinner("Creating your combined schedule…"):
                    plan = generate_multi_subject_plan(subjects_info)
                st.markdown(f'<div class="card">{plan}</div>', unsafe_allow_html=True)
                st.download_button("📥 Download", data=plan,
                    file_name="combined_study_plan.txt", mime="text/plain")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — PYQ ANALYZER
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div class='card' style='background:linear-gradient(135deg,#fff0f5,#f5eaff);'>
      <div style='display:flex;align-items:center;gap:12px;'>
        <div style='font-size:2rem;'>📊</div>
        <div>
          <div style='font-family:"Playfair Display",serif;font-size:1.2rem;color:#c45c78;font-weight:600;'>
            Previous Year Question Analyzer</div>
          <div style='font-size:0.82rem;color:#8c7080;margin-top:2px;'>
            Upload PYQ PDFs → topic frequency, exam predictions, and study priorities</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        pyq_files   = st.file_uploader("Upload PYQ PDF(s)", type=["pdf"],
                        accept_multiple_files=True, key="pyq_up")
        pyq_subject = st.text_input("Subject name", placeholder="e.g. DBMS, Operating Systems")
    with col2:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#fff0f5,#f5eaff);border-radius:14px;
                    padding:16px;border:1.5px solid #f0dde6;font-size:0.82rem;color:#3d2c35;margin-top:8px;'>
          <strong>💡 How it works</strong><br><br>
          1️⃣ Upload 1–3 years of PYQ papers<br><br>
          2️⃣ Enter the subject name<br><br>
          3️⃣ Get topic frequency & predictions<br><br>
          4️⃣ Compare across years for patterns
        </div>
        """, unsafe_allow_html=True)

    if st.button("🔍 Analyze PYQs", type="primary", use_container_width=True):
        if not pyq_files or not pyq_subject:
            st.warning("Please upload at least one PYQ PDF and enter the subject name 🌸")
        else:
            st.session_state.pyq_analyses = []
            progress = st.progress(0)
            for i, pf in enumerate(pyq_files):
                progress.progress((i + 1) / len(pyq_files), text=f"Analyzing {pf.name}…")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pf.read()); path = tmp.name
                try:
                    st.session_state.pyq_analyses.append(
                        analyze_pyq(path, pyq_subject, original_filename=pf.name))
                except Exception as e:
                    st.error(f"Error analyzing {pf.name}: {e}")
                finally:
                    os.unlink(path)
            progress.empty()

    if st.session_state.pyq_analyses:
        for analysis in st.session_state.pyq_analyses:
            with st.expander(f"📄 {analysis['filename']}", expanded=True):
                col1, col2 = st.columns([3, 2])
                with col1:
                    raw = analysis["analysis"]
                    sections = {"TOPICS": [], "FREQUENTLY_ASKED": [], "PREDICTIONS": [],
                                "DIFFICULTY": "", "STUDY_ADVICE": []}
                    current = None
                    for line in raw.split("\n"):
                        for sec in sections:
                            if f"{sec}:" in line:
                                current = sec; break
                        else:
                            if current and line.strip():
                                if isinstance(sections[current], list):
                                    sections[current].append(
                                        line.strip().lstrip("-•123456789. "))
                                else:
                                    sections[current] += " " + line.strip()

                    if sections["FREQUENTLY_ASKED"]:
                        st.markdown("<div class='pyq-section-title'>🔁 Frequently Asked Topics</div>",
                                    unsafe_allow_html=True)
                        for item in sections["FREQUENTLY_ASKED"][:6]:
                            if item:
                                st.markdown(f"<div class='file-pill' style='margin:3px 0;"
                                            f"border-radius:10px;display:block;'>• {item}</div>",
                                            unsafe_allow_html=True)

                    if sections["PREDICTIONS"]:
                        st.markdown("<div class='pyq-section-title'>🎯 Exam Predictions</div>",
                                    unsafe_allow_html=True)
                        colors = ["#e8829a", "#b784a7", "#d4b8e0", "#c45c78", "#8c7080"]
                        for j, pred in enumerate(sections["PREDICTIONS"][:5], 1):
                            if pred:
                                st.markdown(
                                    f"<div style='background:white;border:1.5px solid #f0dde6;"
                                    f"border-left:4px solid {colors[j-1]};border-radius:0 10px 10px 0;"
                                    f"padding:8px 14px;margin:4px 0;font-size:0.84rem;'>"
                                    f"<strong>{j}.</strong> {pred}</div>", unsafe_allow_html=True)

                    if sections["DIFFICULTY"]:
                        st.markdown("<div class='pyq-section-title'>📈 Difficulty Assessment</div>",
                                    unsafe_allow_html=True)
                        st.info(sections["DIFFICULTY"].strip())

                    if sections["STUDY_ADVICE"]:
                        st.markdown("<div class='pyq-section-title'>💡 Study Advice</div>",
                                    unsafe_allow_html=True)
                        for tip in sections["STUDY_ADVICE"][:3]:
                            if tip:
                                st.markdown(f"✨ {tip}")

                with col2:
                    if analysis["chart_data"] and len(analysis["chart_data"]) > 1:
                        st.markdown("<div class='pyq-section-title'>📊 Topic Frequency</div>",
                                    unsafe_allow_html=True)
                        import pandas as pd
                        df = (pd.DataFrame(list(analysis["chart_data"].items()),
                                           columns=["Topic", "Questions"])
                              .sort_values("Questions", ascending=False).head(8))
                        st.bar_chart(df.set_index("Topic"), color="#e8829a")

                    if analysis["predictions"]:
                        st.markdown("<div class='pyq-section-title'>🔥 Top Predicted Topics</div>",
                                    unsafe_allow_html=True)
                        for j, pred in enumerate(analysis["predictions"], 1):
                            st.markdown(f"<div style='font-size:0.78rem;margin:6px 0 2px;'>"
                                        f"{pred[:30]}</div>", unsafe_allow_html=True)
                            st.progress(max(10, 90 - j * 15) / 100)

        if len(st.session_state.pyq_analyses) >= 2:
            st.divider()
            st.markdown("<div style='font-family:\"Playfair Display\",serif;font-size:1.1rem;"
                        "color:#c45c78;font-weight:600;margin-bottom:12px;'>"
                        "📈 Multi-Year Comparison</div>", unsafe_allow_html=True)
            if st.button("🔄 Compare All Years", use_container_width=True, type="primary"):
                with st.spinner("Comparing PYQ patterns across years…"):
                    comparison = compare_pyqs(st.session_state.pyq_analyses)
                st.markdown(f'<div class="card">{comparison}</div>', unsafe_allow_html=True)
                st.download_button("📥 Download Analysis", data=comparison,
                    file_name=f"pyq_analysis_{pyq_subject}.txt", mime="text/plain")