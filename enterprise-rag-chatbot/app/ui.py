"""
app/ui.py  —  StudyMind AI
Claude-style chatbot: sidebar history, streaming, clean minimal UI
"""
import os, sys, tempfile, json, time, html as _html
from pathlib import Path
from datetime import datetime, date
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyMind AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── THEME CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Variables ── */
:root {
  --bg:        #0f0f11;
  --surface:   #1a1a1f;
  --surface2:  #222228;
  --border:    #2e2e38;
  --border2:   #3a3a48;
  --text:      #e8e8f0;
  --muted:     #7a7a90;
  --accent:    #7c6af7;
  --accent2:   #9f94fa;
  --accent-bg: rgba(124,106,247,0.12);
  --green:     #3ecf8e;
  --amber:     #f59e0b;
  --red:       #f87171;
  --radius:    12px;
  --radius-lg: 20px;
}

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
  background: var(--bg) !important;
  font-family: 'Sora', sans-serif !important;
  color: var(--text) !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 99px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
  width: 280px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

/* ── Main area ── */
.main .block-container {
  padding: 0 !important;
  max-width: 100% !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stChatInput"] textarea {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
  font-family: 'Sora', sans-serif !important;
  font-size: 0.88rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(124,106,247,0.20) !important;
}
[data-testid="stChatInput"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 16px !important;
  box-shadow: 0 0 0 1px rgba(124,106,247,0.0) !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(124,106,247,0.18) !important;
}

/* ── Buttons ── */
[data-testid="stButton"] button {
  font-family: 'Sora', sans-serif !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  border-radius: var(--radius) !important;
  transition: all 0.16s !important;
  border: 1px solid transparent !important;
}
[data-testid="stButton"] button[kind="primary"] {
  background: var(--accent) !important;
  color: #fff !important;
  box-shadow: 0 2px 12px rgba(124,106,247,0.35) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
  background: var(--accent2) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 20px rgba(124,106,247,0.45) !important;
}
[data-testid="stButton"] button[kind="secondary"] {
  background: var(--surface2) !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
  border-color: var(--accent) !important;
  color: var(--accent2) !important;
}

/* ── Selects, expanders, metrics ── */
[data-testid="stSelectbox"] > div > div {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
}
[data-testid="stExpander"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}
[data-testid="stExpander"] summary { color: var(--text) !important; }

[data-testid="metric-container"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 16px 18px !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: var(--accent2) !important;
  font-weight: 600 !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
  color: var(--muted) !important;
  font-size: 0.75rem !important;
}

/* ── Progress ── */
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
  background: var(--surface2) !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
  padding: 4px !important;
  gap: 2px !important;
}
[data-testid="stTabs"] [role="tab"] {
  border-radius: 8px !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  color: var(--muted) !important;
  border: none !important;
  transition: all 0.16s !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: var(--accent) !important;
  color: #fff !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
  border-radius: var(--radius) !important;
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
  background: var(--surface2) !important;
  color: var(--accent2) !important;
  border-color: var(--border) !important;
}

/* ── Toggle ── */
[data-testid="stToggle"] { accent-color: var(--accent) !important; }

/* ── Slider ── */
[data-testid="stSlider"] > div > div > div {
  background: var(--accent) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--surface2) !important;
  border: 1px dashed var(--border2) !important;
  border-radius: var(--radius) !important;
}

/* ── dividers ── */
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
}

/* ── Animations ── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Custom components ── */
.sb-header {
  padding: 20px 16px 12px;
  border-bottom: 1px solid var(--border);
}
.sb-logo {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 16px;
}
.sb-logo-icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(135deg, var(--accent), #b06ef7);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.9rem; flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(124,106,247,0.4);
}
.sb-logo-text { font-weight: 600; font-size: 0.95rem; color: var(--text); }
.sb-logo-sub  { font-size: 0.70rem; color: var(--muted); margin-top: 1px; }

.new-chat-btn {
  width: 100%;
  background: var(--accent-bg) !important;
  border: 1px solid rgba(124,106,247,0.30) !important;
  color: var(--accent2) !important;
  border-radius: var(--radius) !important;
  padding: 9px 14px !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  display: flex; align-items: center; gap: 8px;
  cursor: pointer; transition: all 0.16s;
}
.new-chat-btn:hover {
  background: rgba(124,106,247,0.20) !important;
  border-color: var(--accent) !important;
}

.sb-section-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  padding: 12px 16px 6px;
}

.hist-btn {
  width: 100%;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius);
  padding: 8px 12px;
  font-size: 0.80rem;
  color: var(--muted);
  text-align: left;
  cursor: pointer;
  transition: all 0.14s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex; align-items: center; gap: 8px;
}
.hist-btn:hover {
  background: var(--surface2);
  border-color: var(--border);
  color: var(--text);
}
.hist-btn.active {
  background: var(--accent-bg);
  border-color: rgba(124,106,247,0.3);
  color: var(--accent2);
}

.user-chip {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px;
  border-top: 1px solid var(--border);
  background: var(--surface);
}
.user-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), #b06ef7);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.72rem; font-weight: 700; color: #fff;
  flex-shrink: 0;
}
.user-name  { font-size: 0.82rem; font-weight: 500; color: var(--text); }
.user-sub   { font-size: 0.68rem; color: var(--muted); }

/* ── Chat area ── */
.chat-wrap {
  display: flex; flex-direction: column;
  height: 100vh; overflow: hidden;
  background: var(--bg);
}
.chat-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 28px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  flex-shrink: 0;
}
.chat-topbar-title {
  font-size: 0.88rem; font-weight: 500; color: var(--text);
}
.chat-topbar-meta {
  font-size: 0.72rem; color: var(--muted);
  display: flex; align-items: center; gap: 10px;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
  display: inline-block;
}

.chat-msgs {
  flex: 1; overflow-y: auto;
  padding: 28px 0;
  display: flex; flex-direction: column; gap: 0;
}
.msg-row {
  display: flex; gap: 14px;
  padding: 6px 28px;
  animation: fadeUp 0.22s ease;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}
.msg-row.user-row { flex-direction: row-reverse; }

.msg-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.78rem; font-weight: 600;
  flex-shrink: 0; margin-top: 2px;
}
.msg-avatar.ai-av {
  background: linear-gradient(135deg, var(--accent), #b06ef7);
  color: #fff;
  box-shadow: 0 2px 8px rgba(124,106,247,0.35);
}
.msg-avatar.user-av {
  background: var(--surface2);
  border: 1px solid var(--border2);
  color: var(--text);
}

.msg-bubble {
  flex: 1; padding: 13px 16px;
  border-radius: 16px;
  font-size: 0.88rem;
  line-height: 1.65;
  max-width: 720px;
}
.msg-bubble.ai-bubble {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 4px 16px 16px 16px;
}
.msg-bubble.user-bubble {
  background: var(--accent);
  color: #fff;
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 2px 14px rgba(124,106,247,0.30);
}
.msg-meta {
  font-size: 0.68rem; color: var(--muted);
  margin-top: 5px; display: flex; align-items: center; gap: 8px;
}
.msg-meta.right { justify-content: flex-end; }

.source-tag {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 0.70rem;
  color: var(--muted);
  margin: 6px 4px 0 0;
  font-family: 'JetBrains Mono', monospace;
}
.grounded-tag {
  display: inline-flex; align-items: center; gap: 4px;
  background: rgba(62,207,142,0.12);
  border: 1px solid rgba(62,207,142,0.30);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 0.70rem;
  color: var(--green);
  margin-top: 6px;
}
.ungrounded-tag {
  background: rgba(245,158,11,0.12);
  border-color: rgba(245,158,11,0.30);
  color: var(--amber);
}

.fb-row { display: flex; gap: 6px; margin-top: 8px; }
.fb-btn {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 7px; padding: 4px 10px; font-size: 0.75rem;
  color: var(--muted); cursor: pointer; transition: all 0.14s;
}
.fb-btn:hover { border-color: var(--accent); color: var(--accent2); }

.fq-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.fq-chip {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 5px 11px;
  font-size: 0.76rem;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.14s;
  display: inline-block;
}
.fq-chip:hover {
  border-color: var(--accent);
  color: var(--accent2);
  background: var(--accent-bg);
}

.typing-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent); display: inline-block; margin: 0 2px;
  animation: pulse 1.2s ease-in-out infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

/* ── Empty state ── */
.empty-state {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 40px 24px; text-align: center;
  animation: fadeUp 0.4s ease;
}
.empty-icon {
  width: 64px; height: 64px; border-radius: 18px;
  background: linear-gradient(135deg, var(--accent), #b06ef7);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.8rem; margin: 0 auto 20px;
  box-shadow: 0 8px 32px rgba(124,106,247,0.4);
}
.empty-title {
  font-size: 1.5rem; font-weight: 600;
  color: var(--text); margin-bottom: 8px;
}
.empty-sub { font-size: 0.88rem; color: var(--muted); margin-bottom: 32px; }

.sample-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 10px; max-width: 560px; width: 100%;
}
.sample-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  font-size: 0.82rem;
  color: var(--muted);
  cursor: pointer;
  text-align: left;
  transition: all 0.16s;
  line-height: 1.45;
}
.sample-card:hover {
  border-color: var(--accent);
  color: var(--text);
  background: var(--accent-bg);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(124,106,247,0.15);
}
.sample-card-icon { font-size: 1.1rem; margin-bottom: 6px; display: block; }

/* ── Input area ── */
.input-area {
  flex-shrink: 0;
  padding: 16px 28px 20px;
  background: var(--bg);
  border-top: 1px solid var(--border);
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
}
.input-hint {
  text-align: center; font-size: 0.70rem;
  color: var(--muted); margin-top: 8px;
}

/* ── Login ── */
.login-outer {
  min-height: 100vh; display: flex;
  align-items: center; justify-content: center;
  background: var(--bg);
}
.login-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 36px 32px;
  width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  animation: fadeUp 0.35s ease;
}
.login-logo {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 28px;
}
.login-logo-icon {
  width: 42px; height: 42px; border-radius: 11px;
  background: linear-gradient(135deg, var(--accent), #b06ef7);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem;
  box-shadow: 0 4px 14px rgba(124,106,247,0.4);
}
.login-logo-text h2 {
  font-size: 1.1rem; font-weight: 600; color: var(--text);
}
.login-logo-text p { font-size: 0.75rem; color: var(--muted); margin-top: 1px; }
.login-card h3 { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.login-card .sub { font-size: 0.80rem; color: var(--muted); margin-bottom: 22px; }

/* ── File pill ── */
.file-pill {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 0.75rem;
  color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
}

/* ── PYQ sections ── */
.pyq-heading {
  font-size: 0.78rem; font-weight: 600;
  color: var(--accent2);
  text-transform: uppercase; letter-spacing: 0.6px;
  margin: 14px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
}
.pred-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 0 var(--radius) var(--radius) 0;
  padding: 8px 12px;
  font-size: 0.83rem;
  color: var(--text);
  margin: 4px 0;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .sample-grid { grid-template-columns: 1fr; }
  .msg-row { padding: 6px 14px; }
  .input-area { padding: 12px 14px 16px; }
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# AUTH  HELPERS
# ═══════════════════════════════════════════════════════
DATA_DIR   = Path(__file__).parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
HIST_DIR   = DATA_DIR / "chat_history"

try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False

def _hash_password(pw: str) -> str:
    """Hash password with bcrypt + auto-generated salt."""
    if _BCRYPT_AVAILABLE:
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    # Fallback if bcrypt not installed (should not happen in production)
    import hashlib, secrets
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((salt + pw).encode()).hexdigest()

def _check_password(pw: str, stored: str) -> bool:
    """Verify a password against a stored bcrypt hash (or legacy SHA-256 hash)."""
    if _BCRYPT_AVAILABLE and stored.startswith("$2"):
        # Modern bcrypt hash
        return bcrypt.checkpw(pw.encode(), stored.encode())
    # Legacy SHA-256 (no salt) — support read-only for existing accounts
    import hashlib
    if ":" in stored:
        salt, digest = stored.split(":", 1)
        return hashlib.sha256((salt + pw).encode()).hexdigest() == digest
    return hashlib.sha256(pw.encode()).hexdigest() == stored

def _load_users():
    DATA_DIR.mkdir(exist_ok=True)
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    default = {"admin": {"password": _hash_password("admin123"), "name": "Admin",
                         "created": datetime.utcnow().isoformat()}}
    USERS_FILE.write_text(json.dumps(default, indent=2))
    return default

def _save_users(u): USERS_FILE.write_text(json.dumps(u, indent=2))

def auth_login(username, password):
    u = _load_users()
    if username not in u: return False, "User not found"
    if not _check_password(password, u[username]["password"]): return False, "Wrong password"
    return True, u[username]["name"]

def auth_register(username, password, name):
    u = _load_users()
    if username in u: return False, "Username taken"
    if len(password) < 6: return False, "Password min 6 chars"
    u[username] = {"password": _hash_password(password), "name": name,
                   "created": datetime.utcnow().isoformat()}
    _save_users(u); return True, "Account created!"


# ═══════════════════════════════════════════════════════
# CHAT  HISTORY  HELPERS
# ═══════════════════════════════════════════════════════
def _hist_dir(username):
    d = HIST_DIR / username; d.mkdir(parents=True, exist_ok=True); return d

def new_sid():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S") + f"_{int(time.time()*1000)%9999:04d}"

def save_session(username, sid, title, messages):
    p = _hist_dir(username) / f"{sid}.json"
    p.write_text(json.dumps({"id": sid, "title": title,
        "updated": datetime.utcnow().isoformat(), "messages": messages},
        indent=2, ensure_ascii=False))

def load_sessions(username):
    out = []
    for f in sorted(_hist_dir(username).glob("*.json"), reverse=True):
        try:
            d = json.loads(f.read_text())
            out.append({"id": f.stem, "title": d.get("title","Chat"),
                        "updated": d.get("updated",""), "messages": d.get("messages",[])})
        except Exception: pass
    return out

def del_session(username, sid):
    p = _hist_dir(username) / f"{sid}.json"
    if p.exists(): p.unlink()


# ═══════════════════════════════════════════════════════
# SESSION  STATE
# ═══════════════════════════════════════════════════════
_defs = {
    "logged_in": False, "username": None, "user_name": None, "auth_page": "login",
    "sid": None, "title": "New Chat", "messages": [], "history": [],
    "pending": None, "show_summary": None, "plan_result": None, "pyq_analyses": [],
    "model_ready": False,
}
for k, v in _defs.items():
    if k not in st.session_state: st.session_state[k] = v


# ═══════════════════════════════════════════════════════
# LOGIN  WALL
# ═══════════════════════════════════════════════════════
if not st.session_state.logged_in:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("""
        <div style='display:flex;align-items:center;gap:12px;margin-bottom:28px;'>
          <div style='width:42px;height:42px;border-radius:11px;
               background:linear-gradient(135deg,#7c6af7,#b06ef7);
               display:flex;align-items:center;justify-content:center;font-size:1.1rem;
               box-shadow:0 4px 14px rgba(124,106,247,0.4);'>✦</div>
          <div>
            <div style='font-size:1.05rem;font-weight:600;color:#e8e8f0;'>StudyMind AI</div>
            <div style='font-size:0.73rem;color:#7a7a90;'>Your intelligent study assistant</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.auth_page == "login":
            st.markdown("<div style='background:#1a1a1f;border:1px solid #2e2e38;border-radius:16px;padding:28px;'>",
                        unsafe_allow_html=True)
            st.markdown("<div style='font-size:1rem;font-weight:600;color:#e8e8f0;margin-bottom:4px;'>Welcome back</div>",
                        unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.80rem;color:#7a7a90;margin-bottom:20px;'>Sign in to continue</div>",
                        unsafe_allow_html=True)
            u = st.text_input("Username", placeholder="username", key="li_u",
                              label_visibility="collapsed")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            p = st.text_input("Password", type="password", placeholder="password",
                              key="li_p", label_visibility="collapsed")
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("Sign in →", type="primary", use_container_width=True):
                if u and p:
                    ok, msg = auth_login(u, p)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.username  = u
                        st.session_state.user_name = msg
                        st.session_state.sid = new_sid()
                        st.rerun()
                    else: st.error(msg)
                else: st.warning("Fill in both fields")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;font-size:0.80rem;color:#7a7a90;'>"
                        "No account yet?</div>", unsafe_allow_html=True)
            if st.button("Create account", use_container_width=True):
                st.session_state.auth_page = "register"; st.rerun()
        else:
            st.markdown("<div style='background:#1a1a1f;border:1px solid #2e2e38;border-radius:16px;padding:28px;'>",
                        unsafe_allow_html=True)
            st.markdown("<div style='font-size:1rem;font-weight:600;color:#e8e8f0;margin-bottom:4px;'>Create account</div>",
                        unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.80rem;color:#7a7a90;margin-bottom:20px;'>Start your study journey</div>",
                        unsafe_allow_html=True)
            rn = st.text_input("Full name", placeholder="Your name", key="rg_n", label_visibility="collapsed")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            ru = st.text_input("Username", placeholder="Choose username", key="rg_u", label_visibility="collapsed")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            rp = st.text_input("Password", type="password", placeholder="Min 6 chars", key="rg_p", label_visibility="collapsed")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            rp2= st.text_input("Confirm password", type="password", placeholder="Repeat password", key="rg_p2", label_visibility="collapsed")
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("Create account →", type="primary", use_container_width=True):
                if rp != rp2: st.error("Passwords don't match")
                elif rn and ru and rp:
                    ok, msg = auth_register(ru, rp, rn)
                    if ok:
                        st.success(f"{msg} Sign in below.")
                        st.session_state.auth_page = "login"; st.rerun()
                    else: st.error(msg)
                else: st.warning("Fill all fields")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("← Back to sign in", use_container_width=True):
                st.session_state.auth_page = "login"; st.rerun()
    st.stop()


# ═══════════════════════════════════════════════════════
# GROQ KEY CHECK
# ═══════════════════════════════════════════════════════
if not os.environ.get("GROQ_API_KEY"):
    st.error("**GROQ_API_KEY not set.** Open terminal → `set GROQ_API_KEY=gsk_...` → restart Streamlit")
    st.stop()

# ─── Import project modules ───────────────────────────
from ingestion.ingest import ingest_file, list_ingested_files, get_full_text, delete_file
from app.rag_pipeline import stream_answer, summarize_document, suggest_followups
from app.study_planner import generate_study_plan, generate_multi_subject_plan
from app.pyq_analyzer import analyze_pyq, compare_pyqs
from app.feedback import log_feedback, feedback_summary

if not st.session_state.model_ready:
    with st.spinner("Loading embedding model…"):
        try:
            from ingestion.ingest import get_collection; get_collection()
        except Exception: pass
        st.session_state.model_ready = True


# ═══════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════
def export_md():
    lines = [f"# {st.session_state.title}\n_Exported {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n---"]
    for m in st.session_state.messages:
        role = "**You**" if m["role"]=="user" else "**StudyMind AI**"
        lines.append(f"\n{role}\n\n{m['content']}")
        if m.get("sources"):
            lines.append(f"\n> Sources: {', '.join(m['sources'])}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
with st.sidebar:
    initials = "".join(w[0].upper() for w in st.session_state.user_name.split()[:2])

    # Logo
    st.markdown(f"""
    <div class='sb-header'>
      <div class='sb-logo'>
        <div class='sb-logo-icon'>✦</div>
        <div>
          <div class='sb-logo-text'>StudyMind AI</div>
          <div class='sb-logo-sub'>Groq · Llama 3.3 · RAG</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # New chat
    st.markdown("<div style='padding:10px 12px 0;'>", unsafe_allow_html=True)
    if st.button("＋  New Chat", use_container_width=True, type="primary"):
        if st.session_state.messages:
            save_session(st.session_state.username, st.session_state.sid,
                         st.session_state.title, st.session_state.messages)
        st.session_state.messages = []; st.session_state.history = []
        st.session_state.sid = new_sid(); st.session_state.title = "New Chat"
        st.session_state.show_summary = None; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # History
    sessions = load_sessions(st.session_state.username)
    if sessions:
        st.markdown("<div class='sb-section-label'>Recent</div>", unsafe_allow_html=True)
        for sess in sessions[:25]:
            active = sess["id"] == st.session_state.sid
            label  = sess["title"][:32] + ("…" if len(sess["title"]) > 32 else "")
            c1, c2 = st.columns([9, 2])
            with c1:
                btn_style = "primary" if active else "secondary"
                if st.button(f"{'●  ' if active else '○  '}{label}",
                             key=f"h_{sess['id']}", use_container_width=True):
                    if st.session_state.messages:
                        save_session(st.session_state.username, st.session_state.sid,
                                     st.session_state.title, st.session_state.messages)
                    st.session_state.messages = sess["messages"]
                    st.session_state.history  = [{"role": m["role"],"content": m["content"]}
                                                  for m in sess["messages"]]
                    st.session_state.sid   = sess["id"]
                    st.session_state.title = sess["title"]
                    st.rerun()
            with c2:
                if st.button("✕", key=f"d_{sess['id']}"):
                    del_session(st.session_state.username, sess["id"])
                    if sess["id"] == st.session_state.sid:
                        st.session_state.messages=[]; st.session_state.history=[]
                        st.session_state.sid=new_sid(); st.session_state.title="New Chat"
                    st.rerun()

    # ── Documents section ─────────────────────────────
    st.markdown("<hr style='margin:14px 0;'>", unsafe_allow_html=True)
    st.markdown("<div class='sb-section-label'>Documents</div>", unsafe_allow_html=True)
    with st.expander("Upload & manage", expanded=False):
        uf = st.file_uploader("", type=["pdf","docx","txt"],
                              accept_multiple_files=True, label_visibility="collapsed")
        dtype = st.selectbox("", ["syllabus","timetable","fees","rules","pyq","general"],
                             label_visibility="collapsed")
        if uf and st.button("⚡ Ingest files", type="primary", use_container_width=True):
            prog = st.progress(0)
            for i, f in enumerate(uf):
                prog.progress((i+1)/len(uf), text=f"{f.name}")
                sfx = Path(f.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=sfx) as tmp:
                    tmp.write(f.read()); path = tmp.name
                try:
                    n = ingest_file(path, doc_type=dtype, original_filename=f.name)
                    st.success(f"✅ {f.name[:24]} — {n} chunks")
                except Exception as e: st.error(f"❌ {e}")
                finally: os.unlink(path)
            prog.empty(); st.rerun()

        ingested = list_ingested_files()
        for fn in ingested:
            c1, c2 = st.columns([5,1])
            c1.markdown(f"<div class='file-pill'>📄 {fn[:22]}{'…' if len(fn)>22 else ''}</div>",
                        unsafe_allow_html=True)
            if c2.button("✕", key=f"df_{fn}"):
                try: delete_file(fn); st.rerun()
                except Exception as e: st.error(str(e))
        if not ingested:
            st.markdown("<div style='font-size:0.78rem;color:#7a7a90;padding:6px 0;'>"
                        "No documents yet</div>", unsafe_allow_html=True)

    # ── Settings ──────────────────────────────────────
    st.markdown("<div class='sb-section-label'>Settings</div>", unsafe_allow_html=True)
    with st.expander("Search & display", expanded=False):
        use_hybrid = st.toggle("Hybrid search (BM25 + dense)", value=True)
        use_hyde   = st.toggle("HyDE query rewriting", value=True)
        show_debug = st.toggle("Show debug info", value=False)
        doc_filter = st.selectbox("Filter doc type",
            ["All","syllabus","timetable","fees","rules","pyq","general"])
        active_filter = None if doc_filter=="All" else doc_filter

    # ── Export ────────────────────────────────────────
    with st.expander("Export chat", expanded=False):
        if st.session_state.messages:
            st.download_button("📥 Download Markdown", export_md(),
                f"chat_{datetime.now().strftime('%Y%m%d_%H%M')}.md", "text/markdown",
                use_container_width=True)
        else:
            st.markdown("<div style='font-size:0.78rem;color:#7a7a90;'>No messages yet</div>",
                        unsafe_allow_html=True)

    # ── Feedback ──────────────────────────────────────
    with st.expander("Feedback stats", expanded=False):
        fs = feedback_summary()
        c1, c2 = st.columns(2)
        c1.metric("👍", fs["thumbs_up"])
        c2.metric("👎", fs["thumbs_down"])
        if fs["total"]:
            st.progress(fs["approval_rate"]/100,
                        text=f"{fs['approval_rate']}% positive")

    # ── User pill ─────────────────────────────────────
    st.markdown(f"""
    <div style='position:fixed;bottom:0;left:0;width:280px;z-index:99;'>
      <div class='user-chip'>
        <div class='user-avatar'>{initials}</div>
        <div>
          <div class='user-name'>{st.session_state.user_name}</div>
          <div class='user-sub'>@{st.session_state.username}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        if st.session_state.messages:
            save_session(st.session_state.username, st.session_state.sid,
                         st.session_state.title, st.session_state.messages)
        for k in list(_defs): st.session_state.pop(k, None)
        st.rerun()


# ═══════════════════════════════════════════════════════
# MAIN  TABS
# ═══════════════════════════════════════════════════════
ingested = list_ingested_files()

# Topbar
doc_count_html = (f"<span class='status-dot'></span> {len(ingested)} doc"
                  f"{'s' if len(ingested)!=1 else ''} loaded"
                  if ingested else
                  "<span style='color:#f59e0b;'>⚠ No documents — upload in sidebar</span>")
st.markdown(f"""
<div class='chat-topbar'>
  <div class='chat-topbar-title'>{st.session_state.title}</div>
  <div class='chat-topbar-meta'>{doc_count_html}</div>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_plan, tab_pyq, tab_eval = st.tabs(["💬 Chat", "📅 Study Planner", "📊 PYQ Analyzer", "🧪 RAGAS Eval"])


# ═══════════════════════════════════════════════════════
# TAB 1 — CHAT
# ═══════════════════════════════════════════════════════
with tab_chat:

    # ── Summarise picker ─────────────────────────────
    if ingested:
        if st.session_state.show_summary:
            s = st.session_state.show_summary
            with st.expander(f"📋 Summary — {s['file']}", expanded=True):
                st.markdown(s["text"])
                if st.button("Close ✕", key="close_sum"):
                    st.session_state.show_summary = None; st.rerun()

        col_pick, col_go = st.columns([4, 1])
        with col_pick:
            sel = st.selectbox("", ingested, key="sum_sel", label_visibility="collapsed")
        with col_go:
            if st.button("Summarise", use_container_width=True):
                with st.spinner("Summarising…"):
                    txt = get_full_text(sel)
                    if txt:
                        st.session_state.show_summary = {
                            "file": sel, "text": summarize_document(sel, txt)}
                        st.rerun()

    # ── Empty state ───────────────────────────────────
    if not st.session_state.messages:
        st.markdown("""
        <div class='empty-state'>
          <div class='empty-icon'>✦</div>
          <div class='empty-title'>What would you like to know?</div>
          <div class='empty-sub'>Ask anything about your uploaded study materials</div>
          <div class='sample-grid'>
            <div class='sample-card' onclick='void(0)'>
              <span class='sample-card-icon'>📖</span>
              What topics are in the syllabus?
            </div>
            <div class='sample-card'>
              <span class='sample-card-icon'>📋</span>
              Summarize the attendance rules
            </div>
            <div class='sample-card'>
              <span class='sample-card-icon'>🗓️</span>
              What are the exam guidelines?
            </div>
            <div class='sample-card'>
              <span class='sample-card-icon'>💡</span>
              Explain the grading system
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Message history ───────────────────────────────
    for idx, msg in enumerate(st.session_state.messages):
        t = msg.get("time", "")
        if msg["role"] == "user":
            user_init = "".join(w[0].upper() for w in st.session_state.user_name.split()[:2])
            st.markdown(f"""
            <div class='msg-row user-row'>
              <div class='msg-avatar user-av'>{user_init}</div>
              <div>
                <div class='msg-bubble user-bubble'>{msg['content']}</div>
                <div class='msg-meta right'>{t}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            badges = "".join(f"<span class='source-tag'>📄 {s}</span>"
                             for s in msg.get("sources", []))
            grnd = ""
            if "grounded" in msg:
                if msg["grounded"]:
                    grnd = "<span class='grounded-tag'>✓ Verified</span>"
                else:
                    grnd = "<span class='grounded-tag ungrounded-tag'>⚠ Verify manually</span>"

            st.markdown(f"""
            <div class='msg-row'>
              <div class='msg-avatar ai-av'>✦</div>
              <div style='flex:1;'>
                <div class='msg-bubble ai-bubble'>{msg['content']}</div>
                <div style='margin-top:6px;'>{badges}{grnd}</div>
                <div class='msg-meta'>{t}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if msg.get("warning"):
                st.markdown(f"""
                <div style='max-width:860px;margin:0 auto;padding:0 28px 0 74px;'>
                  <div style='background:rgba(245,158,11,0.10);border:1px solid rgba(245,158,11,0.25);
                       border-radius:8px;padding:8px 12px;font-size:0.78rem;color:#f59e0b;'>
                    ⚠ {msg['warning']}
                  </div>
                </div>""", unsafe_allow_html=True)

            if show_debug and msg.get("debug"):
                with st.expander("Debug", expanded=False):
                    st.json(msg["debug"])

            if msg.get("followups"):
                fq_html = "".join(f"<span class='fq-chip'>{q}</span>"
                                   for q in msg["followups"])
                st.markdown(f"""
                <div style='max-width:860px;margin:0 auto;padding:4px 28px 0 74px;'>
                  <div style='font-size:0.70rem;color:#7a7a90;margin-bottom:5px;'>
                    You might also ask:
                  </div>
                  <div class='fq-row'>{fq_html}</div>
                </div>""", unsafe_allow_html=True)

                for fq in msg["followups"]:
                    if st.button(fq, key=f"fq_{idx}_{fq[:10]}", help="Click to ask this"):
                        st.session_state.pending = fq; st.rerun()

            if not msg.get("rated"):
                c1, c2, _ = st.columns([1,1,14])
                if c1.button("👍", key=f"up_{idx}"):
                    log_feedback(msg.get("query",""), msg["content"], msg.get("sources",[]),"up")
                    st.session_state.messages[idx]["rated"] = True; st.rerun()
                if c2.button("👎", key=f"dn_{idx}"):
                    log_feedback(msg.get("query",""), msg["content"], msg.get("sources",[]),"down")
                    st.session_state.messages[idx]["rated"] = True; st.rerun()

    # ── Chat input ────────────────────────────────────
    query = st.chat_input("Ask about your documents…")
    if st.session_state.pending:
        query = st.session_state.pending
        st.session_state.pending = None

    if query:
        if not st.session_state.messages:
            st.session_state.title = query[:44] + ("…" if len(query)>44 else "")
        now = datetime.now().strftime("%H:%M")
        st.session_state.messages.append({"role":"user","content":query,"time":now})

        user_init = "".join(w[0].upper() for w in st.session_state.user_name.split()[:2])
        st.markdown(f"""
        <div class='msg-row user-row'>
          <div class='msg-avatar user-av'>{user_init}</div>
          <div>
            <div class='msg-bubble user-bubble'>{query}</div>
            <div class='msg-meta right'>{now}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # Streaming AI response
        st.markdown("""
        <div class='msg-row' id='ai-typing'>
          <div class='msg-avatar ai-av'>✦</div>
          <div class='msg-bubble ai-bubble'>
            <span class='typing-dot'></span>
            <span class='typing-dot'></span>
            <span class='typing-dot'></span>
          </div>
        </div>""", unsafe_allow_html=True)

        ph   = st.empty()
        full = ""; meta = {}

        for token in stream_answer(query, st.session_state.history,
                                   use_hyde, use_hybrid, active_filter):
            if isinstance(token, dict):
                meta = token
            else:
                full += token
                safe = _html.escape(full)
                ph.markdown(f"""
                <div class='msg-row'>
                  <div class='msg-avatar ai-av'>✦</div>
                  <div>
                    <div class='msg-bubble ai-bubble'>{safe}<span style='opacity:0.4;animation:pulse 0.8s infinite;'>▌</span></div>
                  </div>
                </div>""", unsafe_allow_html=True)

        ph.empty()

        srcs     = meta.get("sources", [])
        grounded = meta.get("grounded", True)
        warn     = None if grounded else "This answer may not be fully backed by the uploaded documents."

        followups = []
        try: followups = suggest_followups(query, full, srcs)
        except Exception: pass

        st.session_state.messages.append({
            "role": "assistant", "content": full,
            "sources": srcs, "grounded": grounded, "warning": warn,
            "query": query, "rated": False, "followups": followups, "time": now,
            "debug": {"rewritten_query": meta.get("rewritten_query"),
                      "chunks_used": meta.get("chunks_used")},
        })
        st.session_state.history += [{"role":"user","content":query},
                                      {"role":"assistant","content":full}]
        save_session(st.session_state.username, st.session_state.sid,
                     st.session_state.title, st.session_state.messages)
        st.rerun()


# ═══════════════════════════════════════════════════════
# TAB 2 — STUDY PLANNER
# ═══════════════════════════════════════════════════════
with tab_plan:
    st.markdown("""
    <div style='background:#1a1a1f;border:1px solid #2e2e38;border-radius:16px;
         padding:20px 24px;margin-bottom:20px;display:flex;align-items:center;gap:14px;'>
      <div style='font-size:1.8rem;'>📅</div>
      <div>
        <div style='font-weight:600;font-size:1rem;color:#e8e8f0;'>Study Planner</div>
        <div style='font-size:0.80rem;color:#7a7a90;margin-top:2px;'>
          AI-generated day-by-day schedule from your syllabus</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    pt1, pt2 = st.tabs(["Single Subject", "Multiple Subjects"])

    with pt1:
        c1, c2 = st.columns(2)
        with c1:
            subject   = st.text_input("Subject", placeholder="e.g. DBMS, OS, CN")
            exam_date = st.date_input("Exam date", min_value=date.today())
            hours_day = st.slider("Hours per day", 1, 12, 4)
        with c2:
            difficulty = st.selectbox("Level", ["beginner","medium","advanced"],
                format_func=lambda x: {"beginner":"🌱 Beginner","medium":"🌿 Medium",
                                        "advanced":"🌳 Advanced"}[x])
            st.markdown("""
            <div style='background:#222228;border:1px solid #2e2e38;border-radius:12px;
                 padding:14px 16px;font-size:0.80rem;color:#7a7a90;margin-top:8px;'>
              <strong style='color:#9f94fa;'>💡 Tip:</strong> Upload your syllabus PDF first
              for a more accurate, topic-specific plan.
            </div>""", unsafe_allow_html=True)

        if st.button("Generate Study Plan →", type="primary", use_container_width=True):
            if not subject: st.warning("Enter a subject name")
            else:
                with st.spinner(f"Building plan for {subject}…"):
                    result = generate_study_plan(subject, exam_date.strftime("%Y-%m-%d"),
                                                  hours_day, difficulty)
                st.session_state.plan_result = result

        if st.session_state.plan_result:
            r = st.session_state.plan_result
            if "error" in r: st.error(r["error"])
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Subject", r["subject"])
                c2.metric("Days left", r["days_left"])
                c3.metric("Total hours", r["total_hours"])
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(r["plan"])
                st.download_button("📥 Download plan", r["plan"],
                    f"plan_{r['subject']}_{r['exam_date']}.md", "text/markdown",
                    use_container_width=True)

    with pt2:
        n = st.number_input("Number of subjects", 2, 6, 3)
        subjects_info = []
        cols = st.columns(3)
        for i in range(n):
            with cols[i%3]:
                st.markdown(f"<div style='font-size:0.78rem;font-weight:600;color:#9f94fa;"
                            f"margin-bottom:6px;'>Subject {i+1}</div>", unsafe_allow_html=True)
                sub   = st.text_input("Name", key=f"ms{i}", placeholder="DBMS")
                edate = st.date_input("Exam date", key=f"md{i}", min_value=date.today())
                prio  = st.selectbox("Priority", ["high","medium","low"], key=f"mp{i}",
                    format_func=lambda x: {"high":"🔴 High","medium":"🟡 Medium","low":"🟢 Low"}[x])
                if sub: subjects_info.append({"subject":sub,
                    "exam_date":edate.strftime("%Y-%m-%d"),"priority":prio})

        if st.button("Generate Combined Plan →", type="primary", use_container_width=True):
            if len(subjects_info) < 2: st.warning("Enter at least 2 subjects")
            else:
                with st.spinner("Creating combined schedule…"):
                    plan = generate_multi_subject_plan(subjects_info)
                st.markdown(plan)
                st.download_button("📥 Download", plan, "combined_plan.md", "text/markdown")


# ═══════════════════════════════════════════════════════
# TAB 3 — PYQ ANALYZER
# ═══════════════════════════════════════════════════════
with tab_pyq:
    st.markdown("""
    <div style='background:#1a1a1f;border:1px solid #2e2e38;border-radius:16px;
         padding:20px 24px;margin-bottom:20px;display:flex;align-items:center;gap:14px;'>
      <div style='font-size:1.8rem;'>📊</div>
      <div>
        <div style='font-weight:600;font-size:1rem;color:#e8e8f0;'>PYQ Analyzer</div>
        <div style='font-size:0.80rem;color:#7a7a90;margin-top:2px;'>
          Topic frequency · Exam predictions · Multi-year patterns</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        pyq_files   = st.file_uploader("Upload PYQ PDFs", type=["pdf"],
                        accept_multiple_files=True, key="pyq_up")
        pyq_subject = st.text_input("Subject name", placeholder="e.g. DBMS, Operating Systems")
    with c2:
        st.markdown("""
        <div style='background:#222228;border:1px solid #2e2e38;border-radius:12px;
             padding:16px;font-size:0.80rem;color:#7a7a90;margin-top:8px;'>
          <strong style='color:#9f94fa;'>How it works</strong><br><br>
          1 · Upload 1–3 years of PYQ papers<br><br>
          2 · Enter subject name<br><br>
          3 · Get frequency analysis &amp; predictions<br><br>
          4 · Compare years for repeating patterns
        </div>""", unsafe_allow_html=True)

    if st.button("Analyze PYQs →", type="primary", use_container_width=True):
        if not pyq_files or not pyq_subject:
            st.warning("Upload at least one PDF and enter subject name")
        else:
            st.session_state.pyq_analyses = []
            prog = st.progress(0)
            for i, pf in enumerate(pyq_files):
                prog.progress((i+1)/len(pyq_files), text=f"Analyzing {pf.name}…")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pf.read()); path = tmp.name
                try:
                    result = analyze_pyq(path, pyq_subject, original_filename=pf.name)
                    if isinstance(result, dict) and "error" in result:
                        st.error(f"{pf.name}: {result['error']}")
                    else:
                        st.session_state.pyq_analyses.append(result)
                except Exception as e: st.error(f"{pf.name}: {e}")
                finally: os.unlink(path)
            prog.empty()

    for analysis in st.session_state.pyq_analyses:
        with st.expander(f"📄 {analysis['filename']}", expanded=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                raw = analysis["analysis"]
                sections = {"TOPICS":[],"FREQUENTLY_ASKED":[],"PREDICTIONS":[],"DIFFICULTY":"","STUDY_ADVICE":[]}
                cur = None
                for line in raw.split("\n"):
                    for sec in sections:
                        if f"{sec}:" in line: cur=sec; break
                    else:
                        if cur and line.strip():
                            if isinstance(sections[cur], list):
                                sections[cur].append(line.strip().lstrip("-•123456789. "))
                            else: sections[cur] += " " + line.strip()

                if sections["FREQUENTLY_ASKED"]:
                    st.markdown("<div class='pyq-heading'>🔁 Frequently Asked</div>",
                                unsafe_allow_html=True)
                    for item in sections["FREQUENTLY_ASKED"][:6]:
                        if item: st.markdown(f"- {item}")

                if sections["PREDICTIONS"]:
                    st.markdown("<div class='pyq-heading'>🎯 Exam Predictions</div>",
                                unsafe_allow_html=True)
                    colors=["#7c6af7","#9f94fa","#b06ef7","#3ecf8e","#7a7a90"]
                    for j, pred in enumerate(sections["PREDICTIONS"][:5],1):
                        if pred:
                            st.markdown(f"""
                            <div class='pred-card' style='border-left-color:{colors[j-1]};'>
                              <strong style='color:{colors[j-1]};'>{j}.</strong> {pred}
                            </div>""", unsafe_allow_html=True)

                if sections["DIFFICULTY"]:
                    st.markdown("<div class='pyq-heading'>📈 Difficulty</div>",
                                unsafe_allow_html=True)
                    st.info(sections["DIFFICULTY"].strip())

                if sections["STUDY_ADVICE"]:
                    st.markdown("<div class='pyq-heading'>💡 Study Tips</div>",
                                unsafe_allow_html=True)
                    for tip in sections["STUDY_ADVICE"][:3]:
                        if tip: st.markdown(f"→ {tip}")

            with c2:
                if analysis["chart_data"] and len(analysis["chart_data"]) > 1:
                    st.markdown("<div class='pyq-heading'>📊 Topic Frequency</div>",
                                unsafe_allow_html=True)
                    import pandas as pd
                    df = (pd.DataFrame(list(analysis["chart_data"].items()),
                                       columns=["Topic","Questions"])
                          .sort_values("Questions",ascending=False).head(8))
                    st.bar_chart(df.set_index("Topic"), color="#7c6af7")

                if analysis["predictions"]:
                    st.markdown("<div class='pyq-heading'>🔥 Top Predicted</div>",
                                unsafe_allow_html=True)
                    for j, pred in enumerate(analysis["predictions"],1):
                        st.markdown(f"<div style='font-size:0.75rem;color:#7a7a90;"
                                    f"margin:5px 0 2px;'>{pred[:32]}</div>",
                                    unsafe_allow_html=True)
                        st.progress(max(10, 90-j*15)/100)

    if len(st.session_state.pyq_analyses) >= 2:
        st.divider()
        st.markdown("<div style='font-weight:600;font-size:0.90rem;color:#e8e8f0;"
                    "margin-bottom:12px;'>📈 Multi-Year Comparison</div>",
                    unsafe_allow_html=True)
        if st.button("Compare all years →", type="primary", use_container_width=True):
            with st.spinner("Comparing patterns…"):
                comp = compare_pyqs(st.session_state.pyq_analyses)
            st.markdown(comp)
            st.download_button("📥 Download", comp,
                f"pyq_{pyq_subject}.md", "text/markdown")

# ═══════════════════════════════════════════════════════
# TAB 4 — RAGAS EVAL DASHBOARD
# ═══════════════════════════════════════════════════════
with tab_eval:
    st.markdown("""
    <div style='padding:24px 0 8px;'>
      <div style='font-weight:600;font-size:1rem;color:#e8e8f0;'>RAGAS Evaluation Dashboard</div>
      <div style='font-size:0.80rem;color:#7a7a90;margin-top:4px;'>
        Measures retrieval quality: faithfulness, answer relevancy, context precision &amp; recall.
      </div>
    </div>
    """, unsafe_allow_html=True)

    import json as _json, os as _os
    from pathlib import Path as _Path

    _results_path = _Path(__file__).parent.parent / "evaluation" / "ragas_results.json"

    # ── Show cached results if they exist ──────────────────────────────────
    if _results_path.exists():
        try:
            _df_data = _json.loads(_results_path.read_text())
            import pandas as _pd
            _df = _pd.DataFrame(_df_data)

            _metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
            _available = [m for m in _metrics if m in _df.columns]

            if _available:
                st.markdown("<div style='font-size:0.78rem;color:#3ecf8e;margin-bottom:16px;'>"
                            "✓ Results loaded from last evaluation run</div>",
                            unsafe_allow_html=True)

                # Score cards
                _cols = st.columns(len(_available))
                _colors = {"faithfulness": "#7c6af7", "answer_relevancy": "#3ecf8e",
                           "context_precision": "#f59e0b", "context_recall": "#9f94fa"}
                for _col, _m in zip(_cols, _available):
                    _val = _df[_m].mean()
                    _color = _colors.get(_m, "#7c6af7")
                    _col.markdown(f"""
                    <div style='background:#1a1a1f;border:1px solid #2e2e38;border-radius:12px;
                                padding:16px;text-align:center;'>
                      <div style='font-size:1.8rem;font-weight:700;color:{_color};'>{_val:.3f}</div>
                      <div style='font-size:0.72rem;color:#7a7a90;margin-top:4px;'>
                        {_m.replace("_"," ").title()}</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Bar chart
                _summary = _pd.DataFrame({
                    "Metric": [m.replace("_", " ").title() for m in _available],
                    "Score":  [round(_df[m].mean(), 3) for m in _available]
                })
                st.bar_chart(_summary.set_index("Metric"), color="#7c6af7")

                # Per-question breakdown
                with st.expander("Per-question breakdown"):
                    _show_cols = ["question"] + _available if "question" in _df.columns else _available
                    st.dataframe(_df[_show_cols].round(3), use_container_width=True)

                st.download_button("📥 Download results (JSON)", _results_path.read_text(),
                                   "ragas_results.json", "application/json")
        except Exception as _e:
            st.warning(f"Could not parse ragas_results.json: {_e}")

    else:
        st.info("No evaluation results yet. Run the evaluation below to generate scores.")

    st.divider()

    # ── Run evaluation button ───────────────────────────────────────────────
    st.markdown("<div style='font-size:0.85rem;color:#e8e8f0;font-weight:600;"
                "margin-bottom:8px;'>Run Evaluation</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.78rem;color:#7a7a90;margin-bottom:12px;'>"
                "Requires <code>OPENAI_API_KEY</code> set in your environment or <code>.env</code> file. "
                "Evaluation calls OpenAI GPT-4o for scoring — uses ~$0.05–0.20 per run.</div>",
                unsafe_allow_html=True)

    _col_a, _col_b = st.columns(2)
    _run_hybrid = _col_a.toggle("Hybrid retrieval (BM25 + dense)", value=True)
    _run_hyde   = _col_b.toggle("HyDE query rewriting", value=True)

    if st.button("▶  Run RAGAS Evaluation", type="primary", use_container_width=False):
        if not _os.environ.get("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY not set. Add it to your .env file and restart the app.")
        else:
            with st.spinner("Running evaluation — this takes ~1–2 minutes…"):
                try:
                    import sys as _sys
                    _sys.path.insert(0, str(_Path(__file__).parent.parent))
                    from evaluation.evaluate import run_evaluation as _run_eval
                    _scores = _run_eval(use_hybrid=_run_hybrid, use_hyde=_run_hyde)
                    if _scores:
                        st.success("Evaluation complete! Refresh the page to see updated scores.")
                        st.json(_scores)
                    else:
                        st.error("Evaluation returned no results. Check terminal for errors.")
                except Exception as _eval_err:
                    st.error(f"Evaluation failed: {_eval_err}")
