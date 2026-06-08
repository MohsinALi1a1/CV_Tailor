"""
CV Tailor — Professional ATS Resume Builder & Optimizer
========================================================
Production-grade Streamlit application rivaling Enhancv, ResumeWorded & Jobscan.
Features: 7 tools, 3 templates, 16+ ATS checks, visual reports.
"""

from __future__ import annotations

import json
import os
import tempfile
from html import escape as _esc
from pathlib import Path

import streamlit as st
from config import get_settings, OUTPUTS_DIR
from utils.api_clients import set_user_api_key


def _h(value) -> str:
    """HTML-escape any value before interpolating into an unsafe_allow_html block.

    Use this for EVERY piece of data that originated from a parsed resume,
    a JD, or any other user-controlled source.
    """
    return _esc("" if value is None else str(value), quote=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Page Config & Session Init
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.set_page_config(
    page_title="CV Tailor — ATS Resume Builder",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "shared_resume_text" not in st.session_state:
    st.session_state.shared_resume_text = ""
if "shared_resume_data" not in st.session_state:
    st.session_state.shared_resume_data = None
if "shared_resume_filename" not in st.session_state:
    st.session_state.shared_resume_filename = ""
if "user_api_key" not in st.session_state:
    st.session_state.user_api_key = ""

# Apply the per-session API key for the lifetime of THIS script run only.
# This isolates each user's key in a ContextVar instead of mutating process env
# (prevents cross-tenant key leakage on multi-user deployments).
set_user_api_key(st.session_state.get("user_api_key") or None)

settings = get_settings()
T = st.session_state.theme

# ── Color palette ──
if T == "dark":
    BG = "#0E1117"; BG2 = "#161B22"; BG3 = "#1C2333"
    TEXT = "#E6EDF3"; TEXT2 = "#8B949E"; TEXT3 = "#6E7681"
    ACCENT = "#58A6FF"; ACCENT2 = "#3FB950"; ACCENT3 = "#D29922"
    DANGER = "#F85149"; SURFACE = "#21262D"; BORDER = "#30363D"
    CARD = "rgba(22,27,34,0.8)"; GLASS = "rgba(22,27,34,0.6)"
else:
    BG = "#FFFFFF"; BG2 = "#F6F8FA"; BG3 = "#F0F2F5"
    TEXT = "#1F2328"; TEXT2 = "#656D76"; TEXT3 = "#8C959F"
    ACCENT = "#0969DA"; ACCENT2 = "#1A7F37"; ACCENT3 = "#BF8700"
    DANGER = "#CF222E"; SURFACE = "#FFFFFF"; BORDER = "#D0D7DE"
    CARD = "rgba(255,255,255,0.95)"; GLASS = "rgba(246,248,250,0.9)"

SUCCESS = ACCENT2
WARNING = ACCENT3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CSS Styles
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.markdown(f"""<style>
.stApp {{ background: {BG}; color: {TEXT}; }}
section[data-testid="stSidebar"] {{
    background: {BG2}; border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] * {{ color: {TEXT}; }}

@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes scoreReveal {{ from {{ stroke-dashoffset: 314; }} }}

.glass-card {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 1.2rem; margin: 0.5rem 0;
    backdrop-filter: blur(10px); animation: fadeIn 0.4s ease-out;
}}
.glass-card:hover {{ border-color: {ACCENT}40; box-shadow: 0 4px 20px {ACCENT}15; }}

.metric-card {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 0.8rem 0.6rem; text-align: center;
    animation: fadeIn 0.5s ease-out;
}}
.metric-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
.metric-value {{ font-size: 1.6rem; font-weight: 700; color: {ACCENT}; line-height: 1.2; }}
.metric-label {{ font-size: 0.72rem; color: {TEXT2}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}
.metric-sub {{ font-size: 0.7rem; color: {TEXT3}; }}

.score-ring-container {{ text-align: center; padding: 1rem; }}
.score-ring {{ position: relative; display: inline-block; }}
.score-ring svg {{ transform: rotate(-90deg); }}
.score-ring .score-text {{
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    font-size: 2.2rem; font-weight: 800; color: {TEXT};
}}
.score-ring .score-label {{
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, calc(-50% + 22px));
    font-size: 0.7rem; color: {TEXT2}; text-transform: uppercase; letter-spacing: 1px;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 0; background: {BG2}; border-radius: 10px; padding: 4px;
    border: 1px solid {BORDER};
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 8px; padding: 8px 14px; font-weight: 500;
    color: {TEXT2}; transition: all 0.2s;
}}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, {ACCENT}, {ACCENT2});
    color: #fff !important; font-weight: 600; box-shadow: 0 2px 8px {ACCENT}40;
}}

.skill-tag {{
    display: inline-block; padding: 4px 10px; margin: 2px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 500; border: 1px solid transparent;
}}
.skill-matched {{ background: {SUCCESS}18; color: {SUCCESS}; border-color: {SUCCESS}40; }}
.skill-missing {{ background: {DANGER}18; color: {DANGER}; border-color: {DANGER}40; }}
.skill-neutral {{ background: {ACCENT}15; color: {ACCENT}; border-color: {ACCENT}30; }}

.stButton > button {{ border-radius: 8px; font-weight: 600; transition: all 0.2s; border: 1px solid {BORDER}; }}
.stButton > button:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
.stDownloadButton > button {{
    border-radius: 8px; font-weight: 600;
    background: linear-gradient(135deg, {ACCENT}, {ACCENT2}) !important;
    color: #fff !important; border: none !important;
}}

.check-item {{
    display: flex; align-items: flex-start; gap: 10px; padding: 10px 14px;
    margin: 4px 0; border-radius: 8px; border-left: 3px solid transparent;
    background: {SURFACE}; border: 1px solid {BORDER}; animation: fadeIn 0.4s ease-out;
}}
.check-pass {{ border-left-color: {SUCCESS} !important; }}
.check-warn {{ border-left-color: {WARNING} !important; }}
.check-fail {{ border-left-color: {DANGER} !important; }}
.check-icon {{ font-size: 1.1rem; min-width: 20px; }}
.check-content {{ flex: 1; }}
.check-title {{ font-weight: 600; color: {TEXT}; font-size: 0.9rem; }}
.check-desc {{ color: {TEXT2}; font-size: 0.8rem; margin-top: 2px; }}

.cat-header {{
    display: flex; align-items: center; gap: 8px; padding: 8px 0; margin-top: 12px;
    border-bottom: 2px solid {ACCENT}30; margin-bottom: 6px;
}}
.cat-header h4 {{ margin: 0; color: {TEXT}; font-size: 1rem; }}
.cat-badge {{
    background: {ACCENT}18; color: {ACCENT}; padding: 2px 8px; border-radius: 10px;
    font-size: 0.72rem; font-weight: 600;
}}

.progress-bar {{ background: {BG3}; border-radius: 6px; overflow: hidden; height: 8px; margin: 4px 0; }}
.progress-fill {{ height: 100%; border-radius: 6px; transition: width 0.6s ease; background: linear-gradient(90deg, {ACCENT}, {ACCENT2}); }}

.suggestion-card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-left: 3px solid {ACCENT};
    border-radius: 8px; padding: 12px 16px; margin: 6px 0; animation: fadeIn 0.5s ease-out;
}}

.hero {{
    background: linear-gradient(135deg, {ACCENT}15, {ACCENT2}10, {ACCENT3}08);
    border: 1px solid {BORDER}; border-radius: 16px; padding: 2rem;
    text-align: center; margin-bottom: 1rem;
}}
.hero h1 {{ font-size: 2rem; margin: 0; background: linear-gradient(135deg, {ACCENT}, {ACCENT2});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.hero p {{ color: {TEXT2}; margin: 0.5rem 0 0 0; font-size: 1rem; }}

[data-testid="stFileUploader"] {{
    border: 2px dashed {BORDER}; border-radius: 12px; padding: 0.5rem;
}}
[data-testid="stFileUploader"]:hover {{ border-color: {ACCENT}; }}
.stExpander {{ border: 1px solid {BORDER}; border-radius: 10px; }}
</style>""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _score_color(score: float, max_score: float = 100) -> str:
    pct = score / max(max_score, 1) * 100
    if pct >= 75: return SUCCESS
    if pct >= 50: return WARNING
    return DANGER

def _score_ring(score: float, max_val: float = 100, size: int = 140) -> str:
    pct = min(score / max(max_val, 1), 1.0)
    color = _score_color(score, max_val)
    r = size // 2 - 10
    circ = 2 * 3.14159 * r
    offset = circ * (1 - pct)
    return f"""
    <div class="score-ring-container"><div class="score-ring">
        <svg width="{size}" height="{size}">
            <circle cx="{size//2}" cy="{size//2}" r="{r}" fill="none" stroke="{BORDER}" stroke-width="8"/>
            <circle cx="{size//2}" cy="{size//2}" r="{r}" fill="none" stroke="{color}" stroke-width="8"
                    stroke-linecap="round" stroke-dasharray="{circ}" stroke-dashoffset="{offset}"
                    style="animation: scoreReveal 1.2s ease-out forwards;"/>
        </svg>
        <div class="score-text" style="color:{color}">{score:.0f}</div>
        <div class="score-label">/ {max_val:.0f}</div>
    </div></div>"""

def _metric(label: str, value, color: str = ACCENT, sub: str = "") -> str:
    sub_html = f'<div class="metric-sub">{_h(sub)}</div>' if sub else ""
    return (
        f'<div class="metric-card">'
        f'<div class="metric-value" style="color:{color}">{_h(value)}</div>'
        f'<div class="metric-label">{_h(label)}</div>{sub_html}</div>'
    )

def _check_item(status: str, title: str, desc: str = "") -> str:
    icons = {"pass": "✅", "warn": "⚠️", "fail": "❌", "info": "ℹ️"}
    cls = {"pass": "check-pass", "warn": "check-warn", "fail": "check-fail"}.get(status, "")
    desc_html = f'<div class="check-desc">{_h(desc)}</div>' if desc else ""
    return (
        f'<div class="check-item {cls}"><div class="check-icon">{icons.get(status, "ℹ️")}</div>'
        f'<div class="check-content"><div class="check-title">{_h(title)}</div>{desc_html}</div></div>'
    )

def _cat_header(icon: str, title: str, score: str = "") -> str:
    badge = f'<span class="cat-badge">{_h(score)}</span>' if score else ""
    return f'<div class="cat-header"><h4>{_h(icon)} {_h(title)}</h4>{badge}</div>'

def _progress_bar(value: float, max_val: float = 100) -> str:
    pct = min(value / max(max_val, 1) * 100, 100)
    return f'<div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>'

def _skill_tags(skills: list[str], style: str = "neutral") -> str:
    safe_style = style if style in ("matched", "missing", "neutral") else "neutral"
    return "".join(
        f'<span class="skill-tag skill-{safe_style}">{_h(s)}</span>' for s in skills
    )

def _extract_resume_text(uploaded_file) -> str:
    from utils.file_parsers import (
        extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt,
        safe_read_upload, UnsafeUploadError,
    )
    try:
        file_bytes, ext = safe_read_upload(uploaded_file)
    except UnsafeUploadError as e:
        st.error(f"❌ {e}")
        st.stop()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == ".docx":
        return extract_text_from_docx(file_bytes)
    return extract_text_from_txt(file_bytes)

def _get_shared_resume() -> str:
    return st.session_state.get("shared_resume_text", "")

def _set_shared_resume(text: str, filename: str = ""):
    st.session_state.shared_resume_text = text
    if text:
        from utils.file_parsers import text_to_resume_dict
        st.session_state.shared_resume_data = text_to_resume_dict(text)
    if filename:
        st.session_state.shared_resume_filename = filename

def _gen_doc(text: str, fmt: str, template: str) -> tuple:
    from utils.file_parsers import generate_resume_document
    return generate_resume_document(text, fmt, template)

def _strip_markdown(text: str) -> str:
    """Remove markdown formatting from AI-generated text."""
    import re as _r
    # Remove ## headers -> plain text
    text = _r.sub(r'^#{1,6}\s*', '', text, flags=_r.MULTILINE)
    # Remove **bold** -> bold
    text = _r.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Remove *italic* -> italic
    text = _r.sub(r'\*(.+?)\*', r'\1', text)
    # Remove __bold__ -> bold
    text = _r.sub(r'__(.+?)__', r'\1', text)
    # Remove _italic_ -> italic (but not snake_case)
    text = _r.sub(r'(?<![a-zA-Z])_([^_]+)_(?![a-zA-Z])', r'\1', text)
    # Remove ``` code blocks
    text = _r.sub(r'```[\s\S]*?```', '', text)
    # Remove `inline code` -> inline code
    text = _r.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Sidebar
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with st.sidebar:
    st.markdown(f"""<div style="text-align:center; padding:1rem 0;">
        <div style="font-size:2.5rem;">🎯</div>
        <h2 style="margin:0; background: linear-gradient(135deg, {ACCENT}, {ACCENT2});
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;">CV Tailor</h2>
        <p style="color:{TEXT2}; font-size:0.8rem; margin:0;">Pro ATS Resume Builder v2.0</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    tc1, tc2 = st.columns(2)
    with tc1:
        if st.button("🌙 Dark", use_container_width=True, type="primary" if T == "dark" else "secondary"):
            st.session_state.theme = "dark"; st.rerun()
    with tc2:
        if st.button("☀️ Light", use_container_width=True, type="primary" if T == "light" else "secondary"):
            st.session_state.theme = "light"; st.rerun()

    st.markdown("---")
    env_key_present = bool(settings.anthropic_api_key)
    key_input = st.text_input(
        "🔑 Anthropic API Key (this session only)",
        type="password",
        value=st.session_state.get("user_api_key", ""),
        placeholder="✅ .env loaded" if env_key_present else "sk-ant-...",
        help=(
            "Stored only in this browser session and used solely for YOUR requests. "
            "It is never written to disk or shared with other users."
        ),
    )
    # Persist in session_state ONLY — NEVER write to os.environ, which would
    # bleed the key to every user of this process.
    new_key = (key_input or "").strip()
    if new_key != st.session_state.get("user_api_key", ""):
        st.session_state.user_api_key = new_key
        set_user_api_key(new_key or None)

    st.markdown("---")
    template_choice = st.selectbox("🎨 Template", ["professional", "minimal", "modern"], index=0)
    export_format = st.selectbox("📄 Format", ["PDF", "DOCX"], index=0)

    st.markdown("---")
    if st.session_state.get("shared_resume_text"):
        fname = st.session_state.get("shared_resume_filename", "Resume")
        st.success(f"📄 **{fname}** loaded")
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.shared_resume_text = ""
            st.session_state.shared_resume_data = None
            st.session_state.shared_resume_filename = ""
            st.rerun()
    else:
        st.info("📤 Upload resume in any tab")

    st.markdown("---")
    st.markdown(f'<p style="text-align:center; color:{TEXT3}; font-size:0.7rem;">7 Tools • 3 Templates • 16+ Checks</p>', unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Hero
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.markdown(f"""<div class="hero">
    <h1>🎯 CV Tailor — ATS Resume Builder</h1>
    <p>Build, optimize & tailor your resume to beat Applicant Tracking Systems. Powered by AI.</p>
</div>""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Tabs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tab_build, tab_ats, tab_tailor, tab_jd, tab_cover, tab_linkedin, tab_translate, tab_industry, tab_interview, tab_diff = st.tabs([
    "📝 Build CV", "📊 ATS Score", "🎯 Tailor", "🔍 Analyse JD",
    "✉️ Cover Letter", "🔗 LinkedIn", "🌐 Translate",
    "🏭 Industry Intel", "🎤 Interview Prep", "🔀 Compare Versions",
])


# ─────────────────────────────────────────────────────────────
#  TAB 1: Build Resume
# ─────────────────────────────────────────────────────────────

with tab_build:
    st.markdown(f'<h2 style="color:{TEXT}">📝 Build Your Resume</h2>', unsafe_allow_html=True)
    col_in, col_out = st.columns([1, 1], gap="large")

    with col_in:
        st.markdown(f'<p style="color:{TEXT2}">Upload an existing resume or fill the form below.</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Resume (PDF, DOCX, TXT, JSON)",
                                          type=["pdf", "docx", "doc", "txt", "json"], key="build_upload")
        if uploaded_file:
            try:
                resume_text = _extract_resume_text(uploaded_file)
                _set_shared_resume(resume_text, uploaded_file.name)
                from utils.file_parsers import diagnose_parse
                diag = diagnose_parse(resume_text)
                pdata = diag["parsed"]
                fs = diag.get("field_summary", {})

                with st.expander("📋 Parsed Preview", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        for f, l in [("name","Name"),("email","Email"),("phone","Phone"),("location","Location")]:
                            ic = "✅" if pdata.get(f) else "❌"
                            st.markdown(f"{ic} **{l}:** {pdata.get(f,'—')}")
                    with c2:
                        for f, l in [("linkedin","LinkedIn"),("website","Website")]:
                            ic = "✅" if pdata.get(f) else "⚪"
                            st.markdown(f"{ic} **{l}:** {pdata.get(f,'—')}")
                        sp = (pdata.get('summary','') or '')[:100]
                        ic = "✅" if pdata.get('summary') else "❌"
                        st.markdown(f"{ic} **Summary:** {sp}{'…' if len(pdata.get('summary',''))>100 else ''}")

                    st.markdown("---")
                    secs = diag.get("sections_detected", [])
                    if secs:
                        st.markdown(f"**Sections:** {', '.join(s.title() for s in secs)}")

                    cols = st.columns(5)
                    for col, (lb, val) in zip(cols, [
                        ("Skills", fs.get("skills_count", 0)),
                        ("Jobs", fs.get("experience_count", 0)),
                        ("Bullets", fs.get("total_bullets", 0)),
                        ("Education", fs.get("education_count", 0)),
                        ("Projects", fs.get("projects_count", 0)),
                    ]):
                        with col:
                            st.markdown(_metric(lb, val, SUCCESS if val > 0 else DANGER), unsafe_allow_html=True)

                    sk = pdata.get("skills", [])
                    if sk:
                        st.markdown("**Skills:**")
                        st.markdown(_skill_tags(sk[:30], "neutral"), unsafe_allow_html=True)

                    for exp in pdata.get("experience", []):
                        t = exp.get('title',''); c = exp.get('company','')
                        d = f"{exp.get('start_date','')} – {exp.get('end_date','')}".strip(" –")
                        nb = len(exp.get('bullets',[]))
                        st.markdown(f"▸ **{t}** at {c}" + (f" · {d}" if d else "") + f" — {nb} bullets")

                    for edu in pdata.get("education", []):
                        st.markdown(f"🎓 **{edu.get('degree','')}** · {edu.get('institution','')} · {edu.get('graduation_date','')}" + (f" · GPA: {edu['gpa']}" if edu.get('gpa') else ""))

                with st.expander("🔍 Raw Text", expanded=False):
                    st.text_area("raw", resume_text, height=200, label_visibility="collapsed")
            except Exception as e:
                st.error(f"❌ Could not parse: {e}")

        st.markdown("---")
        with st.expander("✏️ Manual Entry", expanded=not bool(uploaded_file)):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Full Name", key="b_name")
                email = st.text_input("Email", key="b_email")
                phone = st.text_input("Phone", key="b_phone")
            with c2:
                location = st.text_input("Location", key="b_loc")
                linkedin = st.text_input("LinkedIn", key="b_li")
                website = st.text_input("Website", key="b_web")
            summary = st.text_area("Professional Summary", height=80, key="b_sum")
            skills_input = st.text_area("Skills (comma-separated)", height=60, key="b_skills",
                                         placeholder="Python, JavaScript, ML...")
            num_exp = st.number_input("Experience entries", 0, 10, 1, key="b_nexp")
            experiences = []
            for i in range(int(num_exp)):
                with st.expander(f"Experience #{i+1}", expanded=(i==0)):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        et = st.text_input("Title", key=f"b_et_{i}")
                        ec = st.text_input("Company", key=f"b_ec_{i}")
                        el = st.text_input("Location", key=f"b_el_{i}")
                    with ec2:
                        es = st.text_input("Start", key=f"b_es_{i}")
                        ee = st.text_input("End", value="Present", key=f"b_ee_{i}")
                    eb = st.text_area("Bullets (one/line)", key=f"b_eb_{i}", height=80)
                    experiences.append({"title":et,"company":ec,"location":el,"start_date":es,"end_date":ee,
                                        "bullets":[b.strip() for b in eb.splitlines() if b.strip()]})
            num_edu = st.number_input("Education entries", 0, 5, 1, key="b_nedu")
            education = []
            for i in range(int(num_edu)):
                with st.expander(f"Education #{i+1}", expanded=(i==0)):
                    ed1, ed2 = st.columns(2)
                    with ed1:
                        edeg = st.text_input("Degree", key=f"b_edeg_{i}")
                        einst = st.text_input("Institution", key=f"b_einst_{i}")
                    with ed2:
                        eloc = st.text_input("Location", key=f"b_eloc_{i}")
                        edate = st.text_input("Grad Date", key=f"b_edate_{i}")
                        egpa = st.text_input("GPA", key=f"b_egpa_{i}")
                    education.append({"degree":edeg,"institution":einst,"location":eloc,
                                      "graduation_date":edate,"gpa":egpa})
            num_proj = st.number_input("Project entries", 0, 10, 0, key="b_nproj")
            projects = []
            for i in range(int(num_proj)):
                with st.expander(f"Project #{i+1}", expanded=(i==0)):
                    pn = st.text_input("Project Name", key=f"b_pn_{i}")
                    pd = st.text_area("Description", key=f"b_pd_{i}", height=60,
                                      placeholder="What did you build? What problem did it solve?")
                    pt = st.text_input("Technologies", key=f"b_pt_{i}",
                                       placeholder="Python, React, Docker...")
                    projects.append({"name":pn, "description":pd, "technologies":pt})

            certs_input = st.text_area("Certifications (one/line)", key="b_certs", height=60)
            langs_input = st.text_input("Languages (comma-separated)", key="b_langs")

            # ── Research Papers ──
            num_papers = st.number_input("Research Paper entries", 0, 20, 0, key="b_npapers")
            research_papers = []
            for i in range(int(num_papers)):
                with st.expander(f"📝 Research Paper #{i+1}", expanded=(i==0)):
                    rp1, rp2 = st.columns(2)
                    with rp1:
                        rp_title = st.text_input("Paper Title", key=f"b_rpt_{i}")
                        rp_authors = st.text_input("Authors", key=f"b_rpa_{i}",
                                                    placeholder="Ali M., Khan S., et al.")
                    with rp2:
                        rp_venue = st.text_input("Journal / Conference", key=f"b_rpv_{i}",
                                                  placeholder="IEEE, ACM, arXiv...")
                        rp_year = st.text_input("Year", key=f"b_rpy_{i}")
                    rp_url = st.text_input("URL / DOI", key=f"b_rpu_{i}", placeholder="https://doi.org/...")
                    research_papers.append({"title":rp_title, "authors":rp_authors,
                                            "venue":rp_venue, "year":rp_year, "url":rp_url})

            # ── Volunteer Work ──
            num_vol = st.number_input("Volunteer Work entries", 0, 10, 0, key="b_nvol")
            volunteer_work = []
            for i in range(int(num_vol)):
                with st.expander(f"🤝 Volunteer #{i+1}", expanded=(i==0)):
                    vc1, vc2 = st.columns(2)
                    with vc1:
                        v_role = st.text_input("Role", key=f"b_vr_{i}")
                        v_org = st.text_input("Organization", key=f"b_vo_{i}")
                    with vc2:
                        v_start = st.text_input("Start", key=f"b_vs_{i}")
                        v_end = st.text_input("End", key=f"b_ve_{i}", value="Present")
                    v_desc = st.text_area("Description", key=f"b_vd_{i}", height=60,
                                          placeholder="What did you do? What impact did you make?")
                    volunteer_work.append({"role":v_role, "organization":v_org,
                                           "start_date":v_start, "end_date":v_end, "description":v_desc})

            # ── Achievements ──
            achievements_input = st.text_area("🏆 Achievements / Awards (one per line)", key="b_achieve", height=60,
                                              placeholder="Dean's List 2024\nHackathon Winner - DevFest 2023")

        st.markdown(f'<div class="glass-card"><b>🧠 AI Enhancement Options</b></div>', unsafe_allow_html=True)
        enhance_ai = st.checkbox("🧠 Enhance with AI", key="b_enhance")
        star_approach = st.checkbox(
            "⭐ Use STAR Approach",
            key="b_star",
            help="Rewrite bullets using **S**ituation → **T**ask → **A**ction → **R**esult format for maximum ATS impact.",
        )
        build_btn = st.button("🚀 Generate Resume", type="primary", use_container_width=True, key="b_gen")

    with col_out:
        st.markdown(f'<h3 style="color:{TEXT}">Preview & Download</h3>', unsafe_allow_html=True)
        if build_btn:
            try:
                from modules.resume_builder import ResumeBuilder
                from modules.templates import export_pdf_template, export_docx_template
                builder = ResumeBuilder()
                if uploaded_file:
                    from utils.file_parsers import parse_upload_to_dict
                    pd = parse_upload_to_dict(uploaded_file)
                    if pd: builder.load_data(pd); st.success("✅ Parsed!")
                    else: st.error("❌ Parse failed."); st.stop()
                else:
                    if not name: st.error("❌ Enter name or upload."); st.stop()
                    builder.set_contact(name, email, phone, location, linkedin, website)
                    builder.set_summary(summary)
                    if skills_input:
                        builder.set_skills([s.strip() for s in skills_input.split(",") if s.strip()])
                    for exp in experiences:
                        if exp["title"]: builder.add_experience(**exp)
                    for edu in education:
                        if edu["degree"]: builder.add_education(**edu)
                    for proj in projects:
                        if proj["name"]: builder.add_project(**proj)
                    if certs_input:
                        for c in certs_input.splitlines():
                            if c.strip(): builder.add_certification(c.strip())
                    if langs_input:
                        builder.set_languages([l.strip() for l in langs_input.split(",") if l.strip()])
                    for paper in research_papers:
                        if paper["title"]: builder.add_research_paper(**paper)
                    for vol in volunteer_work:
                        if vol["role"]: builder.add_volunteer_work(**vol)
                    if achievements_input:
                        for a in achievements_input.splitlines():
                            if a.strip(): builder.add_achievement(a.strip())

                if enhance_ai or star_approach:
                    with st.spinner("🧠 Enhancing" + (" with STAR approach" if star_approach else "") + "..."):
                        try:
                            if star_approach:
                                builder.enhance_with_ai_star()
                            else:
                                builder.enhance_with_ai()
                            st.success("✨ Enhanced" + (" with STAR!" if star_approach else "!"))
                        except Exception as e: st.warning(f"AI failed: {e}")

                data = builder.get_data()
                st.markdown(f"""<div class="glass-card">
                    <h3 style="margin:0 0 0.3rem 0; color:{TEXT};">{_h(data.get('name','Resume'))}</h3>
                    <p style="color:{TEXT2}; font-size:0.85rem; margin:0;">
                        {_h(' · '.join(filter(None, [data.get('email'),data.get('phone'),data.get('location')])))}
                    </p></div>""", unsafe_allow_html=True)

                cols = st.columns(4)
                for col, (lb, val) in zip(cols, [
                    ("Skills", len(data.get('skills',[]))), ("Jobs", len(data.get('experience',[]))),
                    ("Bullets", sum(len(e.get('bullets',[])) for e in data.get('experience',[]))),
                    ("Education", len(data.get('education',[]))),
                ]):
                    with col: st.markdown(_metric(lb, val), unsafe_allow_html=True)

                plain = builder.to_plain_text()
                with st.expander("📄 Plain Text"):
                    st.text_area("p", plain, height=300, label_visibility="collapsed")

                with st.spinner("Generating..."):
                    fmt = export_format.lower()
                    _tmp = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False)
                    _tmp_path = _tmp.name
                    _tmp.close()
                    try:
                        if fmt == "pdf":
                            path = export_pdf_template(data, template_name=template_choice, output_path=_tmp_path)
                        else:
                            path = export_docx_template(data, template_name=template_choice, output_path=_tmp_path)
                        fb = Path(path).read_bytes()
                        mime = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    finally:
                        try:
                            os.unlink(_tmp_path)
                        except OSError:
                            pass

                st.download_button(f"⬇️ Download {fmt.upper()}", data=fb, file_name=f"resume.{fmt}", mime=mime, use_container_width=True)
                st.download_button("💾 JSON", data=json.dumps(data, indent=2), file_name="resume.json", mime="application/json")
            except Exception as e:
                st.error(f"❌ Error: {e}")
                with st.expander("Debug"): st.code(str(e))


# ─────────────────────────────────────────────────────────────
#  TAB 2: ATS Score (16+ Checks)
# ─────────────────────────────────────────────────────────────

with tab_ats:
    st.markdown(f'<h2 style="color:{TEXT}">📊 ATS Resume Checker — 16+ Checks</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{TEXT2}">Detailed analysis across Content, Format, Style, Skills & Sections — rivaling Enhancv & ResumeWorded.</p>', unsafe_allow_html=True)

    ac1, ac2 = st.columns([1, 1], gap="large")
    with ac1:
        ats_file = st.file_uploader("Upload Resume", type=["pdf","docx","txt"], key="ats_file")
        if ats_file:
            _ats_ext = _extract_resume_text(ats_file)
            _set_shared_resume(_ats_ext, ats_file.name)
            st.session_state["_ats_text"] = _ats_ext
        elif "_ats_text" not in st.session_state and _get_shared_resume():
            st.session_state["_ats_text"] = _get_shared_resume()[:5000]
        ats_resume = st.text_area("Resume", height=250, key="ats_resume",
                                   value=st.session_state.get("_ats_text", ""),
                                   placeholder="Paste your resume or upload...")
        if not ats_resume and st.session_state.get("_ats_text"):
            ats_resume = st.session_state["_ats_text"]
        ats_jd_file = st.file_uploader("Upload JD (optional)", type=["pdf","docx","txt"], key="ats_jd_file")
        if ats_jd_file:
            st.session_state["_ats_jd_text"] = _extract_resume_text(ats_jd_file)
        ats_jd = st.text_area("Job Description (optional)", height=150, key="ats_jd",
                               value=st.session_state.get("_ats_jd_text", ""),
                               placeholder="Paste JD for keyword matching...")
        if not ats_jd and st.session_state.get("_ats_jd_text"):
            ats_jd = st.session_state["_ats_jd_text"]
        ats_btn = st.button("📊 Run ATS Analysis", type="primary", use_container_width=True, key="ats_run")

        # Show editable fixed resume if fixes were applied
        if st.session_state.get("_ats_fixed_resume"):
            st.markdown("---")
            st.markdown(f'<div class="glass-card"><b>🔧 Fixed Resume</b> — Edit below then re-run analysis to see improvement</div>', unsafe_allow_html=True)
            fixed_resume = st.text_area("Fixed Resume", st.session_state["_ats_fixed_resume"], height=200, key="ats_fixed_edit")
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                if st.button("📊 Re-Analyse Fixed", type="primary", use_container_width=True, key="ats_reanalyse"):
                    st.session_state["_ats_text"] = fixed_resume
                    st.session_state.pop("_ats_fixed_resume", None)
                    st.rerun()
            with fcol2:
                if st.button("🗑️ Discard Fix", use_container_width=True, key="ats_discard_fix"):
                    st.session_state.pop("_ats_fixed_resume", None)
                    st.rerun()

    # ── Store ATS results in session for persistence ──
    if ats_btn:
        if not ats_resume or len(ats_resume.strip()) < 50:
            st.session_state.pop("_ats_report", None)
            with ac2:
                st.error("❌ Provide a resume (50+ chars).")
        else:
            with ac2:
                with st.spinner("🔍 Running 16+ checks..."):
                    try:
                        import re as _re
                        from modules.ats_optimizer import ATSOptimizer
                        from utils.file_parsers import text_to_resume_dict
                        from utils.text_processing import (extract_keywords, match_keywords, bullet_to_list,
                                                           has_quantified_achievement, starts_with_action_verb, count_words)
                        optimizer = ATSOptimizer()
                        report = optimizer.analyse(ats_resume, ats_jd if ats_jd else None)
                        rd = text_to_resume_dict(ats_resume)
                        bullets = bullet_to_list(ats_resume)
                        st.session_state["_ats_report"] = {
                            "resume": ats_resume, "jd": ats_jd,
                            "report": report, "rd": rd, "bullets": bullets,
                        }
                    except Exception as e:
                        st.session_state.pop("_ats_report", None)
                        st.error(f"❌ Error: {e}")
                        with st.expander("Debug"): st.code(str(e))

    # ── Render ATS results (persistent) ──
    with ac2:
        _ar = st.session_state.get("_ats_report")
        if _ar:
            import re as _re
            from utils.text_processing import (extract_keywords, match_keywords, bullet_to_list,
                                               has_quantified_achievement, starts_with_action_verb, count_words)
            report = _ar["report"]
            rd = _ar["rd"]
            bullets = _ar["bullets"]
            _ats_resume_text = _ar["resume"]
            _ats_jd_text = _ar["jd"]

            st.markdown(_score_ring(report.overall_score), unsafe_allow_html=True)

            for lb, sc, mx in [("Sections",report.section_score,25),("Keywords",report.keyword_score,25),
                               ("Formatting",report.formatting_score,20),("Bullet Quality",report.bullet_quality_score,20),
                               ("Length",report.length_score,10)]:
                c1,c2,c3 = st.columns([2,5,1])
                with c1: st.markdown(f"**{lb}**")
                with c2: st.markdown(_progress_bar(sc, mx), unsafe_allow_html=True)
                with c3: st.markdown(f"<span style='color:{_score_color(sc,mx)}'><b>{sc:.0f}</b>/{mx}</span>", unsafe_allow_html=True)
            st.markdown("---")

            # ── CONTENT ──
            st.markdown(_cat_header("📝","Content Checks","4 checks"), unsafe_allow_html=True)
            has_sum = bool(rd.get("summary"))
            _chk1, _fix1 = st.columns([5,1])
            with _chk1:
                st.markdown(_check_item("pass" if has_sum else "fail","Professional Summary",
                    "Summary included." if has_sum else "Add a 2-3 sentence summary."), unsafe_allow_html=True)
            with _fix1:
                if not has_sum:
                    if st.button("Fix", key="ats_fix_summary", use_container_width=True):
                        fixed = _ats_resume_text
                        if "summary" not in fixed.lower()[:200]:
                            lines = fixed.split("\n", 2)
                            if len(lines) >= 2:
                                fixed = lines[0] + "\n" + lines[1] + "\n\nSummary\n[Write your professional summary here — describe your key skills, domain expertise, and career highlights. Do NOT use generic phrases.]\n\n" + (lines[2] if len(lines)>2 else "")
                            else:
                                fixed = fixed + "\n\nSummary\n[Write your professional summary here — describe your key skills, domain expertise, and career highlights. Do NOT use generic phrases.]\n"
                        st.session_state["_ats_fixed_resume"] = fixed
                        st.rerun()

            tb = len(bullets)
            qu = sum(1 for b in bullets if has_quantified_achievement(b))
            qp = (qu/max(tb,1))*100
            st.markdown(_check_item("pass" if qp>=40 else "warn" if qp>=20 else "fail",
                f"Quantified Achievements — {qu}/{tb} ({qp:.0f}%)",
                "Good metrics!" if qp>=40 else f"Add numbers/% to more bullets."), unsafe_allow_html=True)

            vb = sum(1 for b in bullets if starts_with_action_verb(b))
            vp = (vb/max(tb,1))*100
            st.markdown(_check_item("pass" if vp>=60 else "warn" if vp>=30 else "fail",
                f"Action Verbs — {vb}/{tb} ({vp:.0f}%)",
                "Strong verbs!" if vp>=60 else "Start bullets with: Led, Built, Improved..."), unsafe_allow_html=True)

            wl = _re.findall(r'[a-z]+', _ats_resume_text.lower())
            stop = {'the','a','an','and','or','in','on','at','to','for','of','is','was','with','by','as','from','that','this','it','i','my'}
            wf = {}
            for w in wl:
                if w not in stop and len(w)>3: wf[w]=wf.get(w,0)+1
            rpt = {w:c for w,c in wf.items() if c>5}
            st.markdown(_check_item("pass" if len(rpt)<=2 else "warn",
                f"Word Repetition — {len(rpt)} overused",
                "Good variety!" if len(rpt)<=2 else f"Vary: {', '.join(list(rpt)[:5])}"), unsafe_allow_html=True)

            # ── FORMAT ──
            st.markdown(_cat_header("📐","Format Checks","4 checks"), unsafe_allow_html=True)
            wc = count_words(_ats_resume_text)
            st.markdown(_check_item("pass" if 400<=wc<=800 else "warn" if 300<=wc<=1100 else "fail",
                f"Length — {wc} words",
                "Ideal!" if 400<=wc<=800 else ("Short" if wc<400 else "Long")), unsafe_allow_html=True)

            lb = [b for b in bullets if len(b)>150]
            st.markdown(_check_item("pass" if not lb else "warn",
                f"Bullet Length — {len(lb)} long",
                "Concise!" if not lb else f"{len(lb)} bullets >150 chars."), unsafe_allow_html=True)

            he = bool(rd.get("email")); hp = bool(rd.get("phone")); hl = bool(rd.get("linkedin"))
            cs = sum([he,hp,hl])
            missing_c = ', '.join(f for f,v in [('Email',he),('Phone',hp),('LinkedIn',hl)] if not v)
            st.markdown(_check_item("pass" if cs>=3 else "warn" if cs>=2 else "fail",
                f"Contact Info — {cs}/3",
                "Complete!" if cs>=3 else f"Missing: {missing_c}"), unsafe_allow_html=True)

            fi = report.formatting_issues
            st.markdown(_check_item("pass" if not fi else "warn",
                f"ATS Formatting — {len(fi)} issues",
                "Clean!" if not fi else "; ".join(fi)), unsafe_allow_html=True)

            # ── SECTIONS ──
            st.markdown(_cat_header("📋","Section Checks","4 checks"), unsafe_allow_html=True)
            _all_found = {f.lower() for f in report.sections_found}
            if rd.get("experience"): _all_found.add("experience")
            if rd.get("education"): _all_found.add("education")
            if rd.get("skills"): _all_found.add("skills")
            if rd.get("summary"): _all_found.add("summary")
            if rd.get("projects"): _all_found.add("projects")
            if rd.get("certifications"): _all_found.add("certifications")

            for sec in ["Experience","Education","Skills"]:
                found = any(sec.lower() in f for f in _all_found)
                _schk, _sfix = st.columns([5,1])
                with _schk:
                    st.markdown(_check_item("pass" if found else "fail", f"{sec} Section",
                        "Found." if found else f"Add '{sec}' section."), unsafe_allow_html=True)
                with _sfix:
                    if not found:
                        if st.button("Fix", key=f"ats_fix_sec_{sec}", use_container_width=True):
                            fixed = _ats_resume_text
                            if sec == "Skills":
                                fixed += f"\n\n{sec}\nPython, JavaScript, SQL, Docker, AWS, Git [Add your actual skills]"
                            elif sec == "Experience":
                                fixed += f"\n\n{sec}\n[Job Title] | [Company] | [Date Range]\n- [Achievement with quantified result]\n- [Achievement with quantified result]"
                            elif sec == "Education":
                                fixed += f"\n\n{sec}\n[Degree] | [Institution] | [Year]"
                            st.session_state["_ats_fixed_resume"] = fixed
                            st.rerun()

            rec = ["Summary","Projects","Certifications"]
            rf = sum(1 for r in rec if any(r.lower() in f for f in _all_found))
            _rchk, _rfix = st.columns([5,1])
            with _rchk:
                _missing_rec = [r for r in rec if not any(r.lower() in f for f in _all_found)]
                st.markdown(_check_item("pass" if rf>=2 else "warn",
                    f"Recommended — {rf}/{len(rec)}",
                    "Good!" if rf>=2 else f"Add: {', '.join(_missing_rec)}"), unsafe_allow_html=True)
            with _rfix:
                if rf < 2 and _missing_rec:
                    if st.button("Fix", key="ats_fix_rec", use_container_width=True):
                        fixed = _ats_resume_text
                        for sec in _missing_rec:
                            if sec == "Summary" and "summary" not in fixed.lower():
                                fixed = fixed.split("\n", 2)
                                if len(fixed) >= 2:
                                    fixed = fixed[0] + "\n" + fixed[1] + "\n\nSummary\n[Write your professional summary here — your key skills and career highlights.]\n\n" + (fixed[2] if len(fixed)>2 else "")
                                else:
                                    fixed = "\n".join(fixed) + "\n\nSummary\n[Write your professional summary here — your key skills and career highlights.]\n"
                            elif sec == "Projects" and "project" not in fixed.lower() if isinstance(fixed,str) else True:
                                if isinstance(fixed, list): fixed = "\n".join(fixed)
                                fixed += "\n\nProjects\n[Project Name] — [Brief description with technologies used]"
                            elif sec == "Certifications" and "certif" not in (fixed if isinstance(fixed,str) else "\n".join(fixed)).lower():
                                if isinstance(fixed, list): fixed = "\n".join(fixed)
                                fixed += "\n\nCertifications\n[Your Certification Name]"
                        if isinstance(fixed, list): fixed = "\n".join(fixed)
                        st.session_state["_ats_fixed_resume"] = fixed
                        st.rerun()

            # ── STYLE ──
            st.markdown(_cat_header("🎨","Style Checks","4 checks"), unsafe_allow_html=True)
            pp = _re.findall(r'\b(?:was|were|been|being|is|are)\s+\w+ed\b', _ats_resume_text.lower())
            st.markdown(_check_item("pass" if len(pp)<=2 else "warn",
                f"Active Voice — {len(pp)} passive",
                "Active!" if len(pp)<=2 else "Rewrite passive sentences."), unsafe_allow_html=True)

            buzz = ['results-driven','team player','hard worker','go-getter','self-starter',
                    'think outside the box','synergy','guru','ninja','rockstar','responsible for']
            fb_ = [b for b in buzz if b in _ats_resume_text.lower()]
            st.markdown(_check_item("pass" if not fb_ else "warn",
                f"Buzzwords — {len(fb_)} found",
                "Clean!" if not fb_ else f"Remove: {', '.join(fb_[:5])}"), unsafe_allow_html=True)

            em = rd.get("email","")
            bad_e = any(w in em.lower() for w in ['sexy','hot','babe','420','69','xxx'])
            st.markdown(_check_item("pass" if em and not bad_e else "warn" if not em else "fail",
                "Professional Email",
                "Good." if em and not bad_e else "Use professional email."), unsafe_allow_html=True)

            dm = _re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{4}\b', _ats_resume_text, _re.IGNORECASE)
            ds = _re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', _ats_resume_text)
            di = _re.findall(r'\d{4}-\d{2}', _ats_resume_text)
            df = sum([bool(dm),bool(ds),bool(di)])
            st.markdown(_check_item("pass" if df<=1 else "warn","Date Consistency",
                "Consistent." if df<=1 else "Mixed formats — use 'Mon YYYY'."), unsafe_allow_html=True)

            # ── KEYWORDS ──
            if _ats_jd_text:
                st.markdown(_cat_header("🔑","Keyword Match","vs JD"), unsafe_allow_html=True)
                from utils.text_processing import match_keywords_against_text as _mkat
                jk = extract_keywords(_ats_jd_text, top_n=20)
                mm = _mkat(_ats_resume_text, jk)
                rate = mm.get("match_rate",0)
                st.markdown(f"**Match: {rate:.0f}%**")
                st.markdown(_progress_bar(rate), unsafe_allow_html=True)
                if mm.get("matched"):
                    st.markdown("**✅ Matched:**")
                    st.markdown(_skill_tags(mm["matched"],"matched"), unsafe_allow_html=True)
                if mm.get("missing"):
                    st.markdown("**❌ Missing:**")
                    st.markdown(_skill_tags(mm["missing"],"missing"), unsafe_allow_html=True)
                    # Fix button for missing keywords
                    if st.button("⚡ Add Missing Keywords to Skills", key="ats_fix_kw", use_container_width=True):
                        import re as _fixre3
                        fixed = _ats_resume_text
                        _missing_kw = mm["missing"][:12]
                        skills_pat = _fixre3.compile(
                            r'((?:SKILLS?|Technical\s+Skills|Core\s+Competencies)[:\s]*\n)(.*?)(\n\n|\n[A-Z])',
                            _fixre3.IGNORECASE | _fixre3.DOTALL)
                        m = skills_pat.search(fixed)
                        if m:
                            existing = m.group(2).strip()
                            augmented = existing + ", " + ", ".join(_missing_kw)
                            fixed = fixed[:m.start(2)] + augmented + fixed[m.end(2):]
                        else:
                            fixed += "\n\nSKILLS\n" + ", ".join(_missing_kw)
                        st.session_state["_ats_fixed_resume"] = fixed
                        st.rerun()

            st.markdown("---")
            if report.suggestions:
                st.markdown(f'<h4 style="color:{TEXT}">💡 Suggestions</h4>', unsafe_allow_html=True)
                for si, s in enumerate(report.suggestions):
                    _sgc, _sgf = st.columns([5,1])
                    with _sgc:
                        st.markdown(f'<div class="suggestion-card">{s}</div>', unsafe_allow_html=True)
                    with _sgf:
                        # Show fix for actionable suggestions
                        if any(w in s.lower() for w in ["add a", "add '", "missing", "consider adding"]):
                            if st.button("Fix", key=f"ats_sug_fix_{si}", use_container_width=True):
                                fixed = _ats_resume_text
                                # Detect which section to add
                                for sec_name in ["Summary","Experience","Education","Skills","Certifications","Projects"]:
                                    if sec_name.lower() in s.lower() and sec_name.lower() not in fixed.lower():
                                        if sec_name == "Skills":
                                            fixed += f"\n\n{sec_name}\n[Add your skills here — e.g. Python, SQL, AWS]"
                                        elif sec_name == "Summary":
                                            fixed += f"\n\n{sec_name}\n[Write your professional summary — your key skills and career highlights. Do NOT use generic phrases like '5+ years of experience']"
                                        elif sec_name == "Certifications":
                                            fixed += f"\n\n{sec_name}\n[Add your certifications]"
                                        elif sec_name == "Projects":
                                            fixed += f"\n\n{sec_name}\n[Add your projects]"
                                        else:
                                            fixed += f"\n\n{sec_name}\n[Add your {sec_name.lower()} details]"
                                        break
                                st.session_state["_ats_fixed_resume"] = fixed
                                st.rerun()

            sc4 = st.columns(4)
            for col,(lb,val) in zip(sc4,[("Words",wc),("Bullets",tb),("Quantified",f"{qp:.0f}%"),("Verbs",f"{vp:.0f}%")]):
                with col: st.markdown(_metric(lb,val), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  TAB 3: Tailor  (real-time evaluation + iterative fix loop)
# ─────────────────────────────────────────────────────────────

def _evaluate_match(resume_text: str, jd_text: str) -> dict:
    """Real-time keyword evaluation: resume text vs JD keywords."""
    from utils.text_processing import extract_keywords, match_keywords_against_text
    jd_kws = extract_keywords(jd_text, top_n=30)
    report = match_keywords_against_text(resume_text, jd_kws)
    return report

def _inject_keywords_smart(text: str, keywords: list[str]) -> str:
    """Inject missing keywords into Skills AND naturally into Summary/Experience."""
    import re as _ir
    result = text
    cur_lower = result.lower()

    # Filter out keywords already present
    truly_missing = [k for k in keywords if k.lower() not in cur_lower]
    if not truly_missing:
        return result

    # 1. Inject into Skills section (grouped properly)
    skills_pat = _ir.compile(
        r'((?:Skills|Technical\s+Skills|Core\s+Competencies|Key\s+Skills)[:\s]*\n)(.*?)(\n\n|\n[A-Z]|\Z)',
        _ir.IGNORECASE | _ir.DOTALL)
    m = skills_pat.search(result)
    if m:
        existing = m.group(2).strip()
        existing_lower = existing.lower()
        new_skills = [k for k in truly_missing if k.lower() not in existing_lower]
        if new_skills:
            # Don't duplicate — only add what's missing
            augmented = existing + ", " + ", ".join(new_skills[:15])
            result = result[:m.start(2)] + augmented + result[m.end(2):]
    else:
        # No Skills section — add one
        result += "\n\nSkills\n" + ", ".join(truly_missing[:15])

    # 2. Enhance Summary with key terms (top 3-5 keywords woven naturally)
    remaining = [k for k in truly_missing if k.lower() not in result.lower()][:5]
    if remaining:
        summary_pat = _ir.compile(
            r'((?:Professional\s+Summary|Summary|Profile|Objective)[:\s]*\n)(.*?)(\n\n|\n[A-Z])',
            _ir.IGNORECASE | _ir.DOTALL)
        sm = summary_pat.search(result)
        if sm:
            summary_text = sm.group(2).strip()
            # Add a natural skills phrase
            to_add = [k for k in remaining if k.lower() not in summary_text.lower()]
            if to_add:
                phrase = f" Proficient in {', '.join(to_add[:4])}."
                augmented_summary = summary_text.rstrip('.') + '.' + phrase
                result = result[:sm.start(2)] + augmented_summary + result[sm.end(2):]

    # 3. Inject remaining into first experience bullet as context
    still_missing = [k for k in truly_missing if k.lower() not in result.lower()][:3]
    if still_missing:
        exp_pat = _ir.compile(
            r'((?:Professional\s+Experience|Experience|Work\s+Experience)[:\s]*\n)',
            _ir.IGNORECASE)
        em = exp_pat.search(result)
        if em:
            # Find the first bullet after experience heading
            after_heading = result[em.end():]
            bullet_match = _ir.search(r'^(\s*-\s*)', after_heading, _ir.MULTILINE)
            if bullet_match:
                insert_pos = em.end() + bullet_match.start()
                # Add a context line before first bullet
                context_line = f"  Key focus areas: {', '.join(still_missing)}\n"
                # Only add if not already there
                if "key focus areas" not in result.lower():
                    result = result[:insert_pos] + context_line + result[insert_pos:]

    return result

with tab_tailor:
    st.markdown(f'<h2 style="color:{TEXT}">🎯 Tailor Resume to Job Description</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{TEXT2}">Real-time keyword matching + one-click fixes. Keep fixing until 100% match!</p>', unsafe_allow_html=True)

    tc1, tc2 = st.columns([1,1], gap="large")
    with tc1:
        st.markdown("#### Your Resume")
        tf = st.file_uploader("Upload Resume", type=["pdf","docx","txt"], key="tailor_file")
        if tf:
            _tailor_extracted = _extract_resume_text(tf)
            _set_shared_resume(_tailor_extracted, tf.name)
            st.session_state["_tailor_text"] = _tailor_extracted
        elif "_tailor_text" not in st.session_state and _get_shared_resume():
            st.session_state["_tailor_text"] = _get_shared_resume()[:5000]
        tailor_resume = st.text_area("Resume", height=250, key="tailor_resume",
                                      value=st.session_state.get("_tailor_text", ""))
        if not tailor_resume and st.session_state.get("_tailor_text"):
            tailor_resume = st.session_state["_tailor_text"]

        st.markdown("#### Job Description")
        tjf = st.file_uploader("Upload JD", type=["pdf","docx","txt"], key="tailor_jd_file")
        if tjf:
            st.session_state["_tailor_jd_text"] = _extract_resume_text(tjf)
        tailor_jd = st.text_area("JD", height=200, key="tailor_jd",
                                  value=st.session_state.get("_tailor_jd_text", ""))
        if not tailor_jd and st.session_state.get("_tailor_jd_text"):
            tailor_jd = st.session_state["_tailor_jd_text"]

        use_ai = st.checkbox("🧠 Use AI for smart rewriting", key="tailor_use_ai", value=True,
                              help="**Checked** = AI rewrites your resume to match the JD (best results). "
                                   "**Unchecked** = only injects missing keywords into Skills (fast, no API needed).")
        tailor_btn = st.button("🎯 Tailor Resume", type="primary", use_container_width=True, key="tailor_run")

    # ── Run tailoring and store in session ──
    if tailor_btn:
        if not tailor_resume or not tailor_jd:
            st.session_state.pop("_tailor_result", None)
            with tc2: st.error("❌ Need both resume & JD.")
        else:
            with tc2:
                with st.spinner("🎯 Tailoring..."):
                    try:
                        from modules.resume_tailor import ResumeTailor
                        t = ResumeTailor()
                        r = t.tailor(tailor_resume, tailor_jd, use_ai=use_ai)
                        tt = _strip_markdown(r.get("tailored_resume", ""))

                        # Real-time evaluation of BOTH original and tailored
                        orig_eval = _evaluate_match(tailor_resume, tailor_jd)
                        tail_eval = _evaluate_match(tt, tailor_jd)

                        st.session_state["_tailor_result"] = {
                            "original": tailor_resume,
                            "jd": tailor_jd,
                            "tailored": tt,
                            "orig_eval": orig_eval,
                            "suggestions": r.get("suggestions", []),
                            "fix_count": 0,
                        }
                        st.session_state["_tailored_current"] = tt
                    except Exception as e:
                        st.session_state.pop("_tailor_result", None)
                        st.error(f"❌ Error: {e}")
                        with st.expander("Debug"): st.code(str(e))

    # ── Render results with LIVE evaluation ──
    with tc2:
        _tr = st.session_state.get("_tailor_result")
        if _tr:
            current_text = st.session_state.get("_tailored_current", _tr["tailored"])
            jd_text = _tr["jd"]
            fix_count = _tr.get("fix_count", 0)

            # Live evaluation of current text vs JD
            orig_eval = _tr["orig_eval"]
            live_eval = _evaluate_match(current_text, jd_text)

            orig_rate = orig_eval.get("match_rate", 0)
            live_rate = live_eval.get("match_rate", 0)
            improvement = live_rate - orig_rate

            # ── Score Cards ──
            cols = st.columns(4)
            with cols[0]:
                st.markdown(_metric("Original", f"{orig_rate:.0f}%", _score_color(orig_rate)), unsafe_allow_html=True)
            with cols[1]:
                st.markdown(_metric("Current", f"{live_rate:.0f}%", _score_color(live_rate)), unsafe_allow_html=True)
            with cols[2]:
                imp_color = SUCCESS if improvement > 0 else DANGER
                st.markdown(_metric("Improved", f"+{improvement:.0f}%" if improvement > 0 else f"{improvement:.0f}%", imp_color), unsafe_allow_html=True)
            with cols[3]:
                st.markdown(_metric("Fixes", fix_count, ACCENT), unsafe_allow_html=True)

            # Progress bar
            if live_rate >= 80:
                st.success(f"🎉 Excellent! {live_rate:.0f}% keyword match — ATS-optimized!")
            elif live_rate >= 60:
                st.info(f"👍 Good — {live_rate:.0f}% match. Apply fixes below to get to 80%+")
            else:
                st.warning(f"⚠️ {live_rate:.0f}% match — needs improvement. Use the fix buttons below!")

            st.markdown(f"""<div style="background:#2d2d2d;border-radius:8px;padding:4px;margin:0.5rem 0;">
                <div style="background:linear-gradient(90deg,{_score_color(live_rate)},{ACCENT2});
                    width:{min(live_rate,100)}%;height:24px;border-radius:6px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:0.75rem;font-weight:bold;color:white;">
                    {live_rate:.0f}% Match
                </div></div>""", unsafe_allow_html=True)

            # ── Editable tailored resume ──
            st.text_area("✅ Tailored Resume (editable)", current_text, height=280, key="tailored_out")

            # ── MATCHED keywords ──
            matched = live_eval.get("matched", [])
            missing = live_eval.get("missing", [])

            if matched:
                st.markdown(f"**✅ Matched Keywords ({len(matched)}):**")
                st.markdown(_skill_tags(matched, "matched"), unsafe_allow_html=True)

            # ── MISSING keywords with individual Fix buttons ──
            if missing:
                st.markdown(f"**❌ Missing Keywords ({len(missing)}):**")
                st.markdown(_skill_tags(missing, "missing"), unsafe_allow_html=True)

                st.markdown(f'<div class="glass-card"><b>🛠️ One-Click Fixes</b> — Each fix re-evaluates your score</div>', unsafe_allow_html=True)

                # ── Fix All: Inject all missing keywords at once ──
                if st.button(f"⚡ Fix All — Inject {len(missing)} Missing Keywords", key="fix_all_inject",
                             type="primary", use_container_width=True):
                    fixed = _inject_keywords_smart(current_text, missing)
                    st.session_state["_tailored_current"] = fixed
                    st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                    st.rerun()

                # ── Fix individual missing keywords (top 10) ──
                st.markdown("**Or fix one at a time:**")
                kw_cols_per_row = 3
                for row_start in range(0, min(len(missing), 12), kw_cols_per_row):
                    kw_row = missing[row_start:row_start + kw_cols_per_row]
                    row_cols = st.columns(kw_cols_per_row)
                    for ci, kw in enumerate(kw_row):
                        with row_cols[ci]:
                            if st.button(f"+ {kw}", key=f"fix_kw_{row_start}_{ci}", use_container_width=True):
                                fixed = _inject_keywords_smart(current_text, [kw])
                                st.session_state["_tailored_current"] = fixed
                                st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                st.rerun()

                # ── AI Smart Rewrite ──
                st.markdown("---")
                if st.button("🧠 AI Smart Rewrite — Naturally weave keywords throughout", key="fix_ai_rewrite",
                             use_container_width=True):
                    with st.spinner("🧠 AI is rewriting..."):
                        try:
                            from modules.resume_tailor import ResumeTailor
                            t2 = ResumeTailor()
                            r2 = t2.tailor(current_text, jd_text, use_ai=True)
                            fixed2 = _strip_markdown(r2.get("tailored_resume", current_text))
                            st.session_state["_tailored_current"] = fixed2
                            st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ AI rewrite failed: {e}")

            elif live_rate >= 95:
                st.balloons()
                st.success("🏆 All keywords matched! Your resume is fully optimized!")

            # ── Before vs After Comparison ──
            with st.expander("🔍 Before vs After Comparison", expanded=False):
                cmp1, cmp2 = st.columns(2)
                with cmp1:
                    st.markdown(f"**📄 Original** ({orig_rate:.0f}% match)")
                    st.text_area("orig", _tr["original"], height=250, key="cmp_orig", label_visibility="collapsed")
                with cmp2:
                    st.markdown(f"**✅ Current** ({live_rate:.0f}% match)")
                    st.text_area("current", current_text, height=250, key="cmp_fixed", label_visibility="collapsed")
                orig_words = set(_tr["original"].lower().split())
                cur_words = set(current_text.lower().split())
                added_words = cur_words - orig_words
                if added_words:
                    top_added = sorted(added_words)[:20]
                    st.markdown(f"**🆕 Words added ({len(added_words)}):**")
                    st.markdown(_skill_tags(top_added, "matched"), unsafe_allow_html=True)

            # ── Suggestions with smart fix/implement buttons ──
            _all_suggestions = _tr.get("suggestions", [])
            _dismissed = st.session_state.get("_tailor_dismissed_sug", set())
            _active_suggestions = [(i, s) for i, s in enumerate(_all_suggestions) if i not in _dismissed]

            if _active_suggestions:
                with st.expander(f"💡 Suggestions ({len(_active_suggestions)} remaining)", expanded=True):
                    for idx, s in _active_suggestions:
                        s_lower = s.lower()
                        sc1, sc2 = st.columns([5, 1])
                        with sc1:
                            st.markdown(f'<div class="suggestion-card">{s}</div>', unsafe_allow_html=True)
                        with sc2:
                            # ── Type 1: Match rate warning → Fix by injecting missing keywords ──
                            if any(w in s_lower for w in ["keyword match rate", "matches only", "keyword coverage"]):
                                if missing:
                                    if st.button("Fix", key=f"sug_fix_{idx}", use_container_width=True):
                                        fixed = _inject_keywords_smart(current_text, missing)
                                        st.session_state["_tailored_current"] = fixed
                                        st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                        _dismissed.add(idx)
                                        st.session_state["_tailor_dismissed_sug"] = _dismissed
                                        st.rerun()
                                else:
                                    _dismissed.add(idx)
                                    st.session_state["_tailor_dismissed_sug"] = _dismissed

                            # ── Type 2: Missing keywords list → Fix by injecting those exact keywords ──
                            elif "missing keywords to add" in s_lower:
                                import re as _skre
                                # Extract keywords from the suggestion text after the colon
                                kw_match = _skre.search(r':\s*(.+)$', s)
                                if kw_match:
                                    sug_kws = [k.strip() for k in kw_match.group(1).split(',') if k.strip()]
                                else:
                                    sug_kws = missing[:8]
                                if sug_kws:
                                    if st.button("Fix", key=f"sug_fix_{idx}", use_container_width=True):
                                        fixed = _inject_keywords_smart(current_text, sug_kws)
                                        st.session_state["_tailored_current"] = fixed
                                        st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                        _dismissed.add(idx)
                                        st.session_state["_tailor_dismissed_sug"] = _dismissed
                                        st.rerun()

                            # ── Type 3: Required skills from JD → Fix by injecting into Skills ──
                            elif "required skills from jd" in s_lower:
                                import re as _skre2
                                kw_match = _skre2.search(r':\s*(.+)$', s)
                                if kw_match:
                                    req_skills = [k.strip() for k in kw_match.group(1).split(',') if k.strip()]
                                    # Only inject ones not already present
                                    cur_lower = current_text.lower()
                                    to_add = [sk for sk in req_skills if sk.lower() not in cur_lower]
                                    if to_add:
                                        if st.button("Fix", key=f"sug_fix_{idx}", use_container_width=True):
                                            fixed = _inject_keywords_smart(current_text, to_add)
                                            st.session_state["_tailored_current"] = fixed
                                            st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                            _dismissed.add(idx)
                                            st.session_state["_tailor_dismissed_sug"] = _dismissed
                                            st.rerun()
                                    else:
                                        # All required skills already present — auto-dismiss
                                        st.markdown("✅ Done")
                                        _dismissed.add(idx)
                                        st.session_state["_tailor_dismissed_sug"] = _dismissed

                            # ── Type 4: Nice-to-have skills → Fix by injecting ──
                            elif "nice-to-have" in s_lower:
                                import re as _skre3
                                kw_match = _skre3.search(r':\s*(.+)$', s)
                                if kw_match:
                                    nice_skills = [k.strip() for k in kw_match.group(1).split(',') if k.strip()]
                                    cur_lower = current_text.lower()
                                    to_add = [sk for sk in nice_skills if sk.lower() not in cur_lower]
                                    if to_add:
                                        if st.button("Fix", key=f"sug_fix_{idx}", use_container_width=True):
                                            fixed = _inject_keywords_smart(current_text, to_add)
                                            st.session_state["_tailored_current"] = fixed
                                            st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                            _dismissed.add(idx)
                                            st.session_state["_tailor_dismissed_sug"] = _dismissed
                                            st.rerun()
                                    else:
                                        st.markdown("✅ Done")
                                        _dismissed.add(idx)
                                        st.session_state["_tailor_dismissed_sug"] = _dismissed

                            # ── Type 5: Tip — Mirror exact phrasing → Implement via AI ──
                            elif "mirror" in s_lower and "phrasing" in s_lower:
                                if st.button("Apply", key=f"sug_fix_{idx}", use_container_width=True):
                                    with st.spinner("🧠 AI mirroring JD phrasing..."):
                                        try:
                                            from utils.api_clients import get_claude_client
                                            _cl = get_claude_client()
                                            _prompt = (
                                                "Rewrite this resume to mirror the exact phrasing and terminology from the job description.\n"
                                                "RULES:\n"
                                                "- Replace synonyms with the EXACT words used in the JD.\n"
                                                "- Do NOT add new experience or fabricate information.\n"
                                                "- Do NOT add years of experience unless present in original.\n"
                                                "- Keep all original content, just match wording to JD.\n"
                                                "- Return ONLY the rewritten resume, plain text, no markdown.\n\n"
                                                f"--- JOB DESCRIPTION ---\n{jd_text}\n--- END ---\n\n"
                                                f"--- RESUME ---\n{current_text}\n--- END ---"
                                            )
                                            fixed = _strip_markdown(_cl.generate(_prompt, max_tokens=4096))
                                            st.session_state["_tailored_current"] = fixed
                                            st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                            _dismissed.add(idx)
                                            st.session_state["_tailor_dismissed_sug"] = _dismissed
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ {e}")

                            # ── Type 6: Tip — Quantify achievements → Implement via AI ──
                            elif "quantify" in s_lower and "achievement" in s_lower:
                                if st.button("Apply", key=f"sug_fix_{idx}", use_container_width=True):
                                    with st.spinner("🧠 AI quantifying achievements..."):
                                        try:
                                            from utils.api_clients import get_claude_client
                                            _cl = get_claude_client()
                                            _prompt = (
                                                "Rewrite the bullet points in this resume to include quantified achievements.\n"
                                                "RULES:\n"
                                                "- Add numbers, percentages, dollar amounts, or time saved where reasonable.\n"
                                                "- Do NOT fabricate specific numbers — use reasonable estimates with '~' or 'approximately'.\n"
                                                "- Do NOT change section headings or contact info.\n"
                                                "- Keep the same structure, only enhance bullets.\n"
                                                "- Return ONLY the full resume, plain text, no markdown.\n\n"
                                                f"--- RESUME ---\n{current_text}\n--- END ---"
                                            )
                                            fixed = _strip_markdown(_cl.generate(_prompt, max_tokens=4096))
                                            st.session_state["_tailored_current"] = fixed
                                            st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                            _dismissed.add(idx)
                                            st.session_state["_tailor_dismissed_sug"] = _dismissed
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ {e}")

                            # ── Fallback: generic Fix for anything else mentioning "add" ──
                            elif any(w in s_lower for w in ["add", "include", "consider"]):
                                if st.button("Fix", key=f"sug_fix_{idx}", use_container_width=True):
                                    if missing:
                                        fixed = _inject_keywords_smart(current_text, missing[:8])
                                    else:
                                        fixed = current_text
                                    st.session_state["_tailored_current"] = fixed
                                    st.session_state["_tailor_result"]["fix_count"] = fix_count + 1
                                    _dismissed.add(idx)
                                    st.session_state["_tailor_dismissed_sug"] = _dismissed
                                    st.rerun()

                    # Reset dismissed suggestions button
                    if _dismissed:
                        st.markdown("---")
                        if st.button("🔄 Show all suggestions again", key="sug_reset", use_container_width=True):
                            st.session_state["_tailor_dismissed_sug"] = set()
                            st.rerun()
            elif _all_suggestions and _dismissed:
                st.success(f"✅ All {len(_all_suggestions)} suggestions applied!")
                if st.button("🔄 Show suggestions again", key="sug_reset_done", use_container_width=True):
                    st.session_state["_tailor_dismissed_sug"] = set()
                    st.rerun()

            # ── Downloads ──
            st.markdown("---")
            dl_text = current_text
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                pb, _ = _gen_doc(dl_text, "pdf", template_choice)
                st.download_button("⬇️ PDF", pb, "tailored.pdf", "application/pdf", use_container_width=True, key="dl_t_pdf")
            with ec2:
                db, _ = _gen_doc(dl_text, "docx", template_choice)
                st.download_button("⬇️ DOCX", db, "tailored.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   use_container_width=True, key="dl_t_docx")
            with ec3:
                st.download_button("⬇️ TXT", dl_text, "tailored.txt", "text/plain",
                                   use_container_width=True, key="dl_t_txt")


# ─────────────────────────────────────────────────────────────
#  TAB 4: Analyse JD
# ─────────────────────────────────────────────────────────────

with tab_jd:
    st.markdown(f'<h2 style="color:{TEXT}">🔍 Job Description Analyser</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{TEXT2}">Extract requirements, skills & keywords. Compare with your resume.</p>', unsafe_allow_html=True)

    jc1, jc2 = st.columns([1,1], gap="large")
    with jc1:
        jdf = st.file_uploader("Upload JD", type=["pdf","docx","txt"], key="jd_file")
        if jdf:
            st.session_state["_jd_text"] = _extract_resume_text(jdf)
        jd_text = st.text_area("Job Description", height=250, key="jd_text",
                                value=st.session_state.get("_jd_text", ""))
        if not jd_text and st.session_state.get("_jd_text"):
            jd_text = st.session_state["_jd_text"]
        jrf = st.file_uploader("Upload resume (optional)", type=["pdf","docx","txt"], key="jd_resume_file")
        if jrf:
            _jdr_ext = _extract_resume_text(jrf)
            _set_shared_resume(_jdr_ext, jrf.name)
            st.session_state["_jd_resume_text"] = _jdr_ext
        elif "_jd_resume_text" not in st.session_state and _get_shared_resume():
            st.session_state["_jd_resume_text"] = _get_shared_resume()[:3000]
        jd_resume = st.text_area("Your Resume (optional)", height=150, key="jd_resume",
                                  value=st.session_state.get("_jd_resume_text", ""))
        if not jd_resume and st.session_state.get("_jd_resume_text"):
            jd_resume = st.session_state["_jd_resume_text"]
        noai = st.checkbox("⚡ Skip AI", key="jd_noai")
        jd_btn = st.button("🔍 Analyse", type="primary", use_container_width=True, key="jd_run")

    # ── Store JD results in session ──
    if jd_btn:
        if not jd_text:
            st.session_state.pop("_jd_result", None)
            with jc2: st.error("❌ Provide JD.")
        else:
            with jc2:
                with st.spinner("🔍 Analysing..."):
                    try:
                        from modules.job_analyzer import JobAnalyzer
                        ja = JobAnalyzer()
                        r = ja.compare(jd_text, jd_resume, use_ai=not noai) if jd_resume else ja.analyse(jd_text, use_ai=not noai)
                        st.session_state["_jd_result"] = r
                    except Exception as e:
                        st.session_state.pop("_jd_result", None)
                        st.error(f"❌ Error: {e}")
                        with st.expander("Debug"): st.code(str(e))

    # ── Render JD results (persistent) ──
    with jc2:
        _jr = st.session_state.get("_jd_result")
        if _jr:
            r = _jr
            # Support both dataclass (has .to_dict()) and plain dict
            if hasattr(r, 'to_dict'):
                rd = r.to_dict()
            elif hasattr(r, '__dict__') and not isinstance(r, dict):
                rd = {k: v for k, v in r.__dict__.items() if not k.startswith('_')}
            else:
                rd = r

            if rd.get("match_rate"):
                st.markdown(_score_ring(rd["match_rate"]), unsafe_allow_html=True)

            c1,c2 = st.columns(2)
            with c1:
                if rd.get("required_skills"):
                    st.markdown("**Required:**"); st.markdown(_skill_tags(rd["required_skills"],"neutral"), unsafe_allow_html=True)
                if rd.get("matched_skills"):
                    st.markdown("**✅ You Have:**"); st.markdown(_skill_tags(rd["matched_skills"],"matched"), unsafe_allow_html=True)
            with c2:
                if rd.get("preferred_skills"):
                    st.markdown("**Preferred:**"); st.markdown(_skill_tags(rd["preferred_skills"],"neutral"), unsafe_allow_html=True)
                if rd.get("missing_skills"):
                    st.markdown("**❌ You Need:**"); st.markdown(_skill_tags(rd["missing_skills"],"missing"), unsafe_allow_html=True)
                    # Fix: Copy missing skills for use in Tailor/Builder
                    if st.button("📋 Copy Missing Skills", key="jd_copy_missing", use_container_width=True):
                        st.session_state["_shared_missing_skills"] = rd["missing_skills"]
                        st.success(f"✅ {len(rd['missing_skills'])} skills saved! Use them in Tailor or Builder tab.")

            if rd.get("responsibilities"):
                with st.expander("📋 Responsibilities", expanded=True):
                    for resp in rd["responsibilities"]: st.markdown(f"• {resp}")
            if rd.get("suggestions"):
                with st.expander("💡 Suggestions"):
                    for si, s in enumerate(rd["suggestions"]):
                        _sjc, _sjf = st.columns([5,1])
                        with _sjc:
                            st.markdown(f'<div class="suggestion-card">{s}</div>', unsafe_allow_html=True)
                        with _sjf:
                            if any(w in s.lower() for w in ["add","include","mention","consider","highlight"]):
                                if st.button("📋", key=f"jd_sug_copy_{si}", help="Copy suggestion"):
                                    st.session_state.setdefault("_jd_saved_tips", []).append(s)
                                    st.toast(f"💡 Tip saved!")

            # Show saved tips
            if st.session_state.get("_jd_saved_tips"):
                with st.expander(f"📌 Saved Tips ({len(st.session_state['_jd_saved_tips'])})"):
                    for tip in st.session_state["_jd_saved_tips"]:
                        st.markdown(f"• {tip}")
                    if st.button("🗑️ Clear Tips", key="jd_clear_tips"):
                        st.session_state.pop("_jd_saved_tips", None)
                        st.rerun()


# ─────────────────────────────────────────────────────────────
#  TAB 5: Cover Letter
# ─────────────────────────────────────────────────────────────

with tab_cover:
    st.markdown(f'<h2 style="color:{TEXT}">✉️ AI Cover Letter Generator</h2>', unsafe_allow_html=True)
    cc1, cc2 = st.columns([1,1], gap="large")
    with cc1:
        clf = st.file_uploader("Upload Resume", type=["pdf","docx","txt"], key="cl_file")
        if clf:
            _cl_ext = _extract_resume_text(clf)
            _set_shared_resume(_cl_ext, clf.name)
            st.session_state["_cl_text"] = _cl_ext
        elif "_cl_text" not in st.session_state and _get_shared_resume():
            st.session_state["_cl_text"] = _get_shared_resume()[:3000]
        cl_resume = st.text_area("Resume", height=200, key="cl_resume",
                                  value=st.session_state.get("_cl_text", ""))
        if not cl_resume and st.session_state.get("_cl_text"):
            cl_resume = st.session_state["_cl_text"]
        cljf = st.file_uploader("Upload JD", type=["pdf","docx","txt"], key="cl_jd_file")
        if cljf:
            st.session_state["_cl_jd_text"] = _extract_resume_text(cljf)
        cl_jd = st.text_area("Job Description", height=200, key="cl_jd",
                              value=st.session_state.get("_cl_jd_text", ""))
        if not cl_jd and st.session_state.get("_cl_jd_text"):
            cl_jd = st.session_state["_cl_jd_text"]
        cl_co = st.text_input("Company", key="cl_co")
        cl_role = st.text_input("Role", key="cl_role")
        cl_btn = st.button("✉️ Generate", type="primary", use_container_width=True, key="cl_run")

    # ── Store cover letter in session ──
    if cl_btn:
        if not cl_resume or not cl_jd:
            st.session_state.pop("_cl_result", None)
            with cc2: st.error("❌ Need resume & JD.")
        else:
            with cc2:
                with st.spinner("✉️ Generating..."):
                    try:
                        from modules.bonus_features import generate_cover_letter
                        letter = generate_cover_letter(
                            cl_resume, cl_jd,
                            company_name=cl_co,
                            role=cl_role,
                        )
                        st.session_state["_cl_result"] = letter
                    except Exception as e:
                        st.session_state.pop("_cl_result", None)
                        st.error(f"❌ Error: {e}")
                        with st.expander("Debug"): st.code(str(e))

    # ── Render cover letter (persistent) ──
    with cc2:
        _clr = st.session_state.get("_cl_result")
        if _clr:
            edited_cl = st.text_area("Cover Letter", _clr, height=350, key="cl_out")
            ec1,ec2,ec3 = st.columns(3)
            with ec1:
                pb,_ = _gen_doc(edited_cl,"pdf",template_choice)
                st.download_button("⬇️ PDF",pb,"cover.pdf","application/pdf",use_container_width=True, key="dl_cl_pdf")
            with ec2:
                db,_ = _gen_doc(edited_cl,"docx",template_choice)
                st.download_button("⬇️ DOCX",db,"cover.docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document",use_container_width=True, key="dl_cl_docx")
            with ec3:
                st.download_button("⬇️ TXT",edited_cl,"cover.txt","text/plain",use_container_width=True, key="dl_cl_txt")


# ─────────────────────────────────────────────────────────────
#  TAB 6: LinkedIn
# ─────────────────────────────────────────────────────────────

with tab_linkedin:
    st.markdown(f'<h2 style="color:{TEXT}">🔗 LinkedIn Summary Generator</h2>', unsafe_allow_html=True)
    lc1, lc2 = st.columns([1,1], gap="large")
    with lc1:
        lif = st.file_uploader("Upload Resume", type=["pdf","docx","txt"], key="li_file")
        if lif:
            _li_ext = _extract_resume_text(lif)
            _set_shared_resume(_li_ext, lif.name)
            st.session_state["_li_text"] = _li_ext
        elif "_li_text" not in st.session_state and _get_shared_resume():
            st.session_state["_li_text"] = _get_shared_resume()[:3000]
        li_resume = st.text_area("Resume", height=300, key="li_resume",
                                  value=st.session_state.get("_li_text", ""))
        if not li_resume and st.session_state.get("_li_text"):
            li_resume = st.session_state["_li_text"]
        li_btn = st.button("🔗 Generate", type="primary", use_container_width=True, key="li_run")

    # ── Store LinkedIn result in session ──
    if li_btn:
        if not li_resume:
            st.session_state.pop("_li_result", None)
            with lc2: st.error("❌ Provide resume.")
        else:
            with lc2:
                with st.spinner("🔗 Generating..."):
                    try:
                        from modules.bonus_features import generate_linkedin_summary
                        summary = generate_linkedin_summary(li_resume)
                        st.session_state["_li_result"] = summary
                    except Exception as e:
                        st.session_state.pop("_li_result", None)
                        st.error(f"❌ Error: {e}")
                        with st.expander("Debug"): st.code(str(e))

    # ── Render LinkedIn result (persistent) ──
    with lc2:
        _lir = st.session_state.get("_li_result")
        if _lir:
            edited_li = st.text_area("LinkedIn Summary", _lir, height=300, key="li_out")
            ec1,ec2 = st.columns(2)
            with ec1:
                db,_ = _gen_doc(edited_li,"docx",template_choice)
                st.download_button("⬇️ DOCX",db,"linkedin.docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document",use_container_width=True, key="dl_li_docx")
            with ec2:
                st.download_button("⬇️ TXT",edited_li,"linkedin.txt","text/plain",use_container_width=True, key="dl_li_txt")


# ─────────────────────────────────────────────────────────────
#  TAB 7: Translate
# ─────────────────────────────────────────────────────────────

with tab_translate:
    st.markdown(f'<h2 style="color:{TEXT}">🌐 Resume Translator</h2>', unsafe_allow_html=True)
    trc1, trc2 = st.columns([1,1], gap="large")
    with trc1:
        trf = st.file_uploader("Upload Resume", type=["pdf","docx","txt"], key="tr_file")
        if trf:
            _tr_ext = _extract_resume_text(trf)
            _set_shared_resume(_tr_ext, trf.name)
            st.session_state["_tr_text"] = _tr_ext
        elif "_tr_text" not in st.session_state and _get_shared_resume():
            st.session_state["_tr_text"] = _get_shared_resume()[:3000]
        tr_resume = st.text_area("Resume", height=300, key="tr_resume",
                                  value=st.session_state.get("_tr_text", ""))
        if not tr_resume and st.session_state.get("_tr_text"):
            tr_resume = st.session_state["_tr_text"]
        LANGS = ["Arabic","Chinese (Simplified)","Chinese (Traditional)","Dutch","French","German",
                 "Hindi","Italian","Japanese","Korean","Polish","Portuguese","Russian","Spanish","Turkish","Urdu"]
        tr_lang = st.selectbox("Language", LANGS, key="tr_lang")
        tr_btn = st.button("🌐 Translate", type="primary", use_container_width=True, key="tr_run")

    # ── Store translate result in session ──
    if tr_btn:
        if not tr_resume:
            st.session_state.pop("_tr_result", None)
            with trc2: st.error("❌ Provide resume.")
        else:
            with trc2:
                with st.spinner(f"🌐 Translating to {tr_lang}..."):
                    try:
                        from modules.bonus_features import translate_resume
                        translated = translate_resume(tr_resume, tr_lang)
                        st.session_state["_tr_result"] = {"text": translated, "lang": tr_lang}
                    except Exception as e:
                        st.session_state.pop("_tr_result", None)
                        st.error(f"❌ Error: {e}")
                        with st.expander("Debug"): st.code(str(e))

    # ── Render translate result (persistent) ──
    with trc2:
        _trr = st.session_state.get("_tr_result")
        if _trr:
            _tr_lang_label = _trr["lang"]
            edited_tr = st.text_area(f"{_tr_lang_label}", _trr["text"], height=300, key="tr_out")
            ec1,ec2,ec3 = st.columns(3)
            with ec1:
                pb,_ = _gen_doc(edited_tr,"pdf",template_choice)
                st.download_button("⬇️ PDF",pb,f"resume_{_tr_lang_label}.pdf","application/pdf",use_container_width=True, key="dl_tr_pdf")
            with ec2:
                db,_ = _gen_doc(edited_tr,"docx",template_choice)
                st.download_button("⬇️ DOCX",db,f"resume_{_tr_lang_label}.docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document",use_container_width=True, key="dl_tr_docx")
            with ec3:
                st.download_button("⬇️ TXT",edited_tr,f"resume_{_tr_lang_label}.txt","text/plain",use_container_width=True, key="dl_tr_txt")


# ─────────────────────────────────────────────────────────────
#  TAB 8: Industry Intelligence
# ─────────────────────────────────────────────────────────────

with tab_industry:
    st.markdown(f'<h2 style="color:{TEXT}">🏭 Industry Intelligence</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{TEXT2}">Detect the target industry of a JD and get industry-specific keyword guidance.</p>', unsafe_allow_html=True)

    iic1, iic2 = st.columns([1, 1], gap="large")
    with iic1:
        iijdf = st.file_uploader("Upload JD", type=["pdf", "docx", "txt"], key="ii_jd_file")
        if iijdf:
            st.session_state["_ii_jd_text"] = _extract_resume_text(iijdf)
        ii_jd = st.text_area("Job Description", height=300, key="ii_jd",
                              value=st.session_state.get("_ii_jd_text", ""))
        ii_btn = st.button("🔬 Detect Industry", type="primary", use_container_width=True, key="ii_run")

    if ii_btn:
        if not ii_jd.strip():
            with iic2: st.error("❌ Provide a job description.")
            st.session_state.pop("_ii_result", None)
        else:
            try:
                from modules.industry_intel import detect_industry
                analysis = detect_industry(ii_jd)
                st.session_state["_ii_result"] = analysis.to_dict()
            except Exception as e:
                st.session_state.pop("_ii_result", None)
                with iic2:
                    st.error(f"❌ Error: {e}")

    with iic2:
        _iir = st.session_state.get("_ii_result")
        if _iir:
            st.metric("🏭 Primary Industry", _iir["primary_industry_name"],
                      delta=f"{_iir['confidence']}% confidence")
            if _iir.get("secondary_industries"):
                with st.expander("Secondary Industries"):
                    for sec in _iir["secondary_industries"]:
                        st.write(f"• **{sec['name']}** — score: {sec['score']}")
            st.markdown("#### ✅ Industry Keywords in JD")
            kws = _iir.get("industry_keywords_in_jd", [])
            if kws:
                st.markdown(" ".join([f"`{k}`" for k in kws[:30]]))
            else:
                st.info("No industry-specific keywords detected.")
            st.markdown("#### ⚠️ Suggested Keywords to Add")
            missing = _iir.get("industry_keywords_missing", [])
            if missing:
                st.markdown(" ".join([f"`{k}`" for k in missing[:20]]))
            st.markdown("#### 💡 Industry-Specific ATS Tips")
            for tip in _iir.get("industry_tips", []):
                st.markdown(f"- {tip}")


# ─────────────────────────────────────────────────────────────
#  TAB 9: Interview Prep
# ─────────────────────────────────────────────────────────────

with tab_interview:
    st.markdown(f'<h2 style="color:{TEXT}">🎤 Interview Preparation</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{TEXT2}">Generate tailored interview questions, STAR scaffolds, and prep tips.</p>', unsafe_allow_html=True)

    ipc1, ipc2 = st.columns([1, 1], gap="large")
    with ipc1:
        ip_rf = st.file_uploader("Upload Resume", type=["pdf", "docx", "txt"], key="ip_resume_file")
        if ip_rf:
            _ip_ext = _extract_resume_text(ip_rf)
            _set_shared_resume(_ip_ext, ip_rf.name)
            st.session_state["_ip_resume"] = _ip_ext
        elif "_ip_resume" not in st.session_state and _get_shared_resume():
            st.session_state["_ip_resume"] = _get_shared_resume()[:3000]
        ip_resume = st.text_area("Resume", height=180, key="ip_resume_text",
                                  value=st.session_state.get("_ip_resume", ""))
        ip_jdf = st.file_uploader("Upload JD", type=["pdf", "docx", "txt"], key="ip_jd_file")
        if ip_jdf:
            st.session_state["_ip_jd"] = _extract_resume_text(ip_jdf)
        ip_jd = st.text_area("Job Description", height=180, key="ip_jd_text",
                              value=st.session_state.get("_ip_jd", ""))
        cc_a, cc_b = st.columns(2)
        with cc_a:
            ip_role = st.text_input("Role (optional)", key="ip_role")
        with cc_b:
            ip_company = st.text_input("Company (optional)", key="ip_company")
        ip_use_ai = st.checkbox("✨ Use AI for tailored questions", value=True, key="ip_ai")
        ip_btn = st.button("🎤 Generate Prep", type="primary", use_container_width=True, key="ip_run")

    if ip_btn:
        if not ip_resume.strip() or not ip_jd.strip():
            with ipc2: st.error("❌ Need both resume & JD.")
            st.session_state.pop("_ip_result", None)
        else:
            with ipc2:
                with st.spinner("🎤 Generating interview prep..."):
                    try:
                        from modules.interview_prep import generate_interview_prep
                        prep = generate_interview_prep(
                            resume_text=ip_resume,
                            job_description=ip_jd,
                            role=ip_role,
                            company=ip_company,
                            use_ai=ip_use_ai,
                        )
                        st.session_state["_ip_result"] = prep.to_dict()
                    except Exception as e:
                        st.session_state.pop("_ip_result", None)
                        st.error(f"❌ Error: {e}")
                        with st.expander("Debug"): st.code(str(e))

    with ipc2:
        _ipr = st.session_state.get("_ip_result")
        if _ipr:
            badge = "🤖 AI-powered" if _ipr.get("ai_powered") else "📚 Template-based"
            st.success(badge)
            if _ipr.get("role_specific"):
                with st.expander(f"🎯 Role-Specific Questions ({len(_ipr['role_specific'])})", expanded=True):
                    for i, q in enumerate(_ipr["role_specific"], 1):
                        st.markdown(f"**{i}.** {q['question']}")
            with st.expander(f"🧠 Behavioral Questions ({len(_ipr.get('behavioral', []))})"):
                for i, q in enumerate(_ipr.get("behavioral", []), 1):
                    st.markdown(f"**{i}.** {q['question']}")
            with st.expander(f"⚙️ Technical Questions ({len(_ipr.get('technical', []))})"):
                for i, q in enumerate(_ipr.get("technical", []), 1):
                    st.markdown(f"**{i}.** {q['question']}")
            if _ipr.get("leadership"):
                with st.expander(f"👥 Leadership Questions ({len(_ipr['leadership'])})"):
                    for i, q in enumerate(_ipr["leadership"], 1):
                        st.markdown(f"**{i}.** {q['question']}")
            with st.expander("❓ Questions to Ask the Interviewer"):
                for i, q in enumerate(_ipr.get("questions_to_ask", []), 1):
                    st.markdown(f"**{i}.** {q}")
            with st.expander("💡 Preparation Tips", expanded=True):
                for tip in _ipr.get("preparation_tips", []):
                    st.markdown(f"- {tip}")
            # Download button
            import json as _json
            st.download_button(
                "⬇️ Download Prep (JSON)",
                _json.dumps(_ipr, indent=2),
                "interview_prep.json",
                "application/json",
                use_container_width=True,
                key="dl_ip_json",
            )


# ─────────────────────────────────────────────────────────────
#  TAB 10: Compare Versions (Resume Diff)
# ─────────────────────────────────────────────────────────────

with tab_diff:
    st.markdown(f'<h2 style="color:{TEXT}">🔀 Compare Resume Versions</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{TEXT2}">Side-by-side diff to see exactly what changed between original and tailored versions.</p>', unsafe_allow_html=True)

    dfc1, dfc2 = st.columns([1, 1], gap="large")
    with dfc1:
        df_orig_file = st.file_uploader("Original Resume", type=["pdf", "docx", "txt"], key="df_orig_file")
        if df_orig_file:
            st.session_state["_df_orig"] = _extract_resume_text(df_orig_file)
        df_orig = st.text_area("Original", height=300, key="df_orig_text",
                                value=st.session_state.get("_df_orig", ""))
    with dfc2:
        df_new_file = st.file_uploader("Tailored / New Resume", type=["pdf", "docx", "txt"], key="df_new_file")
        if df_new_file:
            st.session_state["_df_new"] = _extract_resume_text(df_new_file)
        df_new = st.text_area("Tailored", height=300, key="df_new_text",
                               value=st.session_state.get("_df_new", ""))

    df_btn = st.button("🔀 Compare", type="primary", use_container_width=True, key="df_run")

    if df_btn:
        if not df_orig.strip() or not df_new.strip():
            st.error("❌ Provide both versions.")
            st.session_state.pop("_df_result", None)
        else:
            try:
                from modules.resume_diff import diff_resumes
                diff = diff_resumes(df_orig, df_new)
                st.session_state["_df_result"] = {
                    "stats": diff.stats.to_dict(),
                    "html": diff.html_diff,
                    "unified": diff.unified_diff,
                    "summary": diff.summary,
                }
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.session_state.pop("_df_result", None)

    _dfr = st.session_state.get("_df_result")
    if _dfr:
        st.markdown("---")
        st.markdown(f"### 📊 {_dfr['summary']}")
        m1, m2, m3, m4 = st.columns(4)
        s = _dfr["stats"]
        m1.metric("✅ Similarity", f"{s['similarity_pct']}%")
        m2.metric("➕ Lines Added", s["lines_added"])
        m3.metric("➖ Lines Removed", s["lines_removed"])
        m4.metric("🔑 New Keywords", s["words_added"])

        col_a, col_b = st.columns(2)
        with col_a:
            with st.expander(f"✅ Added Keywords ({len(s['keywords_added'])})", expanded=True):
                st.markdown(" ".join([f"`{k}`" for k in s["keywords_added"][:50]]) or "_(none)_")
        with col_b:
            with st.expander(f"⚠️ Removed Keywords ({len(s['keywords_removed'])})"):
                st.markdown(" ".join([f"`{k}`" for k in s["keywords_removed"][:50]]) or "_(none)_")

        with st.expander("🔍 Side-by-Side HTML Diff", expanded=True):
            st.components.v1.html(_dfr["html"], height=600, scrolling=True)

        with st.expander("📋 Unified Diff (Text)"):
            st.code(_dfr["unified"], language="diff")

        st.download_button(
            "⬇️ Download Diff Report (HTML)",
            f"<html><body>{_dfr['html']}</body></html>",
            "resume_diff.html",
            "text/html",
            use_container_width=True,
            key="dl_df_html",
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Footer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.markdown(f"""<div style="text-align:center; padding:1rem;">
    <p style="color:{TEXT3}; font-size:0.8rem;">
        🎯 CV Tailor v2.0 — Pro ATS Resume Builder<br/>
        Built with Streamlit • Claude AI • ReportLab • python-docx<br/>
        © 2026 All rights reserved.</p>
</div>""", unsafe_allow_html=True)
