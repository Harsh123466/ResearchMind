import html
import re
import time
import traceback

import streamlit as st

from graph.workflow import graph

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchMind · AI Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PASS_SCORE = 7  # matches should_continue() in graph/workflow.py

# key, number, title, description
STEPS = [
    ("search", "01", "Search Agent", "Gathers recent web information"),
    ("reader", "02", "Reader Agent", "Scrapes & extracts deep content"),
    ("writer", "03", "Writer Chain", "Drafts the full research report"),
    ("critic", "04", "Critic Chain", "Reviews & scores the report"),
]


# ── Gemini / pipeline error classification (UI only) ─────────────────────────
def _chain(exc):
    """Yield the exception and every exception that caused it."""
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def classify_error(exc) -> dict:
    """Turn a raw exception into a friendly title / message / tip."""
    text = " ".join(str(e) for e in _chain(exc)).lower()
    names = " ".join(type(e).__name__ for e in _chain(exc)).lower()

    codes = set()
    for e in _chain(exc):
        for attr in ("code", "status_code"):
            value = getattr(e, attr, None)
            if isinstance(value, int):
                codes.add(value)
    codes.update(int(c) for c in re.findall(r"\b([45]\d\d)\b", text[:600]))

    if "recursion" in names or "recursion limit" in text:
        return {
            "kind": "loop",
            "title": "The revision loop never finished",
            "message": "The critic kept scoring the report below the pass mark, and the "
                       "writer/critic loop hit LangGraph's step limit.",
            "tip": "In your code, make writer_node increment revision_count so the loop "
                   "stops after 2 rewrites.",
        }

    if (codes & {401, 403}) or any(
        k in text
        for k in ("api key not valid", "api_key_invalid", "permission_denied",
                  "unauthenticated", "api key")
    ):
        return {
            "kind": "auth",
            "title": "API key problem",
            "message": "Google rejected the request. The API key is missing, invalid, "
                       "or not allowed to use this model.",
            "tip": "Check the key in your .env file, then restart the app.",
        }

    if 429 in codes or any(
        k in text for k in ("resource_exhausted", "quota", "rate limit", "too many requests")
    ):
        return {
            "kind": "quota",
            "title": "Rate limit or free-tier quota reached",
            "message": "Too many requests were sent in a short time (or for today). "
                       "This is common on the free tier, since one run makes many calls.",
            "tip": "Wait 1–2 minutes and try again. If it keeps happening, switch to a "
                   "lighter Flash model or enable billing on your API key.",
        }

    if (codes & {500, 502, 503, 504}) or any(
        k in text for k in ("unavailable", "high demand", "overloaded", "internal error")
    ):
        return {
            "kind": "busy",
            "title": "Gemini is busy right now",
            "message": "Google's servers are overloaded. Free-tier requests are the first "
                       "to be delayed. This is temporary and not a bug in your code.",
            "tip": "Wait about a minute, then press Try again.",
        }

    if 404 in codes or ("model" in text and "not found" in text):
        return {
            "kind": "model",
            "title": "Model not found",
            "message": "The model name used in your agent files isn't available for this key.",
            "tip": "Check the model name against the list in Google AI Studio.",
        }

    if any(k in text for k in ("timed out", "timeout", "connection", "network", "deadline")):
        return {
            "kind": "network",
            "title": "Network problem",
            "message": "The request to Google timed out or the connection dropped.",
            "tip": "Check your internet connection, then press Try again.",
        }

    return {
        "kind": "unknown",
        "title": "Something went wrong",
        "message": f"{type(exc).__name__}: {str(exc)[:200]}",
        "tip": "Open the error details below to see the full traceback.",
    }


# ── Themes ────────────────────────────────────────────────────────────────────
# Add or edit a theme here. All colors in the UI come from these values.
#   *_rgb / glow / surface values are "R,G,B" so the CSS can add transparency.
THEMES = {
    "Midnight Orange": dict(
        bg="#0a0a0f", glow1="255,140,50", glow2="255,80,30",
        text="#e8e4dc", heading="#f0ebe0", title="#ffffff",
        muted="#a09890", faint="#706860",
        accent="255,140,50", accent2="#ff5a1a",
        good="80,200,120", bad="255,90,90",
        surface="255,255,255", btn_text="#0a0a0f",
    ),
}

t = THEMES["Midnight Orange"]

# Inject the chosen theme as CSS variables
st.markdown(f"""
<style>
:root {{
    --bg: {t['bg']};
    --glow1: {t['glow1']};
    --glow2: {t['glow2']};
    --text: {t['text']};
    --heading: {t['heading']};
    --title: {t['title']};
    --muted: {t['muted']};
    --faint: {t['faint']};
    --accent-rgb: {t['accent']};
    --accent2: {t['accent2']};
    --good-rgb: {t['good']};
    --bad-rgb: {t['bad']};
    --surface: {t['surface']};
    --btn-text: {t['btn_text']};
}}
</style>
""", unsafe_allow_html=True)

# ── Custom CSS (uses the theme variables above) ──────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}

.stApp {
    background: var(--bg);
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(var(--glow1),0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(var(--glow2),0.08) 0%, transparent 55%);
}

/* Keep markdown text readable in every theme */
.stMarkdown p:not([class]),
.stMarkdown li,
.stMarkdown td,
.stMarkdown th { color: var(--text) !important; }
.stMarkdown h1:not([class]), .stMarkdown h2:not([class]),
.stMarkdown h3:not([class]), .stMarkdown h4:not([class]) { color: var(--heading) !important; }
.stButton button p, .stDownloadButton button p { color: var(--btn-text) !important; }

/* ── Hide default streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1200px; }

/* ── Hero header ── */
.hero { text-align: center; padding: 3.5rem 0 2.5rem; position: relative; }
.hero-eyebrow {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: rgb(var(--accent-rgb));
    margin-bottom: 1rem;
    opacity: 0.9;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.8rem, 6vw, 5rem);
    font-weight: 800;
    line-height: 1.0;
    letter-spacing: -0.03em;
    margin: 0 0 1rem;
}
.hero-white  { color: var(--title) !important; }
.hero-orange { color: rgb(var(--accent-rgb)) !important; }
.hero-sub {
    font-size: 1.05rem;
    font-weight: 300;
    color: var(--muted);
    max-width: 520px;
    margin: 0 auto;
    line-height: 1.65;
}

/* ── Divider ── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(var(--accent-rgb),0.3), transparent);
    margin: 2rem 0;
}

/* ── Bordered panels (st.container with key) ── */
.st-key-input_box,
.st-key-report_box,
.st-key-feedback_box {
    background: rgba(var(--surface),0.03);
    border: 1px solid rgba(var(--accent-rgb),0.15);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(8px);
}
.st-key-report_box   { border-color: rgba(var(--accent-rgb),0.2); }
.st-key-feedback_box { border-color: rgba(var(--good-rgb),0.25); }

/* ── Streamlit input overrides ── */
.stTextInput > div > div > input {
    background: rgba(var(--surface),0.05) !important;
    border: 1px solid rgba(var(--accent-rgb),0.25) !important;
    border-radius: 10px !important;
    color: var(--heading) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgb(var(--accent-rgb)) !important;
    box-shadow: 0 0 0 3px rgba(var(--accent-rgb),0.12) !important;
}
.stTextInput > label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: rgb(var(--accent-rgb)) !important;
    font-weight: 500 !important;
}
.stTextInput > label p { color: rgb(var(--accent-rgb)) !important; }

/* ── Buttons ── */
.stButton > button,
.stDownloadButton > button {
    background: linear-gradient(135deg, rgb(var(--accent-rgb)) 0%, var(--accent2) 100%) !important;
    color: var(--btn-text) !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.04em !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.7rem 2.2rem !important;
    cursor: pointer !important;
    transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s !important;
    box-shadow: 0 4px 20px rgba(var(--accent-rgb),0.3) !important;
    width: 100%;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(var(--accent-rgb),0.4) !important;
    opacity: 0.95 !important;
}
.stButton > button:active,
.stDownloadButton > button:active { transform: translateY(0) !important; }

/* ── Pipeline step cards ── */
.step-card {
    background: rgba(var(--surface),0.03);
    border: 1px solid rgba(var(--surface),0.09);
    border-radius: 14px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s;
}
.step-card.active { border-color: rgba(var(--accent-rgb),0.4);  background: rgba(var(--accent-rgb),0.05); }
.step-card.done   { border-color: rgba(var(--good-rgb),0.35);   background: rgba(var(--good-rgb),0.04); }
.step-card.error  { border-color: rgba(var(--bad-rgb),0.4);     background: rgba(var(--bad-rgb),0.05); }
.step-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    border-radius: 14px 0 0 14px;
    background: rgba(var(--surface),0.08);
    transition: background 0.3s;
}
.step-card.active::before { background: rgb(var(--accent-rgb)); }
.step-card.done::before   { background: rgb(var(--good-rgb)); }
.step-card.error::before  { background: rgb(var(--bad-rgb)); }

.step-header { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.3rem; }
.step-num {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.15em;
    color: rgb(var(--accent-rgb));
    opacity: 0.7;
}
.step-title { font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 700; color: var(--heading); }
.step-status {
    margin-left: auto;
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
}
.status-waiting { color: var(--faint); }
.status-running { color: rgb(var(--accent-rgb)); animation: pulse 1.2s ease-in-out infinite; }
.status-done    { color: rgb(var(--good-rgb)); }
.status-error   { color: rgb(var(--bad-rgb)); }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
.step-desc { font-size: 0.82rem; color: var(--faint); margin-top: 0.3rem; }

/* ── Error panel ── */
.error-panel {
    background: rgba(var(--bad-rgb),0.06);
    border: 1px solid rgba(var(--bad-rgb),0.3);
    border-left: 3px solid rgb(var(--bad-rgb));
    border-radius: 14px;
    padding: 1.6rem 2rem;
    margin: 2rem 0 1rem;
}
.error-eyebrow {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgb(var(--bad-rgb));
    margin-bottom: 0.6rem;
}
.error-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--heading);
    margin-bottom: 0.6rem;
}
.error-msg { font-size: 0.92rem; line-height: 1.7; color: var(--text); margin-bottom: 0.9rem; }
.error-tip {
    font-size: 0.85rem;
    line-height: 1.6;
    color: rgb(var(--accent-rgb));
    background: rgba(var(--accent-rgb),0.08);
    border: 1px solid rgba(var(--accent-rgb),0.22);
    border-radius: 10px;
    padding: 0.7rem 1rem;
}
.error-note { font-size: 0.8rem; color: var(--faint); margin: 0.8rem 0 0; }

/* ── Result panels ── */
.result-panel {
    background: rgba(var(--surface),0.03);
    border: 1px solid rgba(var(--surface),0.09);
    border-radius: 14px;
    padding: 1.8rem 2rem;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
}
.result-panel-title {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgb(var(--accent-rgb));
    margin-bottom: 1rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid rgba(var(--accent-rgb),0.15);
}
.result-content {
    font-size: 0.92rem;
    line-height: 1.8;
    color: var(--text);
    white-space: pre-wrap;
    font-family: 'DM Sans', sans-serif;
}

/* ── Panel labels ── */
.panel-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 1.2rem;
    padding-bottom: 0.7rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}
.panel-label.orange { color: rgb(var(--accent-rgb)); border-bottom: 1px solid rgba(var(--accent-rgb),0.15); }
.panel-label.green  { color: rgb(var(--good-rgb));   border-bottom: 1px solid rgba(var(--good-rgb),0.2); }

/* ── Score / meta chips ── */
.chip {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    padding: 0.2rem 0.65rem;
    border-radius: 6px;
    background: rgba(var(--surface),0.05);
    border: 1px solid rgba(var(--surface),0.1);
    color: var(--muted);
}
.chip.good { color: rgb(var(--good-rgb));   border-color: rgba(var(--good-rgb),0.4);   background: rgba(var(--good-rgb),0.08); }
.chip.warn { color: rgb(var(--accent-rgb)); border-color: rgba(var(--accent-rgb),0.4); background: rgba(var(--accent-rgb),0.08); }
.chip-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.2rem; }

/* ── Progress / spinner ── */
.stSpinner > div { color: rgb(var(--accent-rgb)) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(var(--surface),0.025);
    border: 1px solid rgba(var(--surface),0.09) !important;
    border-radius: 12px;
}
details summary {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
    color: var(--muted) !important;
    letter-spacing: 0.1em !important;
    cursor: pointer;
}
details summary p { color: var(--muted) !important; }

/* ── Section heading ── */
.section-heading {
    font-family: 'Syne', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--heading);
    margin: 2rem 0 1rem;
}

/* ── Footer notice ── */
.notice {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: var(--faint);
    text-align: center;
    margin-top: 3rem;
    letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("results", {})
ss.setdefault("step_states", {k: "waiting" for k, *_ in STEPS})
ss.setdefault("step_notes", {})
ss.setdefault("meta", {})
ss.setdefault("error", None)        # raw traceback text
ss.setdefault("error_info", None)   # friendly dict from classify_error()
ss.setdefault("last_topic", "")
ss.setdefault("pending", None)      # set by the "Try again" button


def queue_retry():
    ss.pending = "retry"


# ── Helpers ───────────────────────────────────────────────────────────────────
def step_html(num: str, title: str, state: str, desc: str) -> str:
    status_map = {
        "waiting": ("WAITING", "status-waiting", ""),
        "running": ("● RUNNING", "status-running", "active"),
        "done": ("✓ DONE", "status-done", "done"),
        "error": ("✕ FAILED", "status-error", "error"),
    }
    label, status_cls, card_cls = status_map.get(state, ("", "", ""))
    return (
        f'<div class="step-card {card_cls}">'
        f'<div class="step-header">'
        f'<span class="step-num">{num}</span>'
        f'<span class="step-title">{title}</span>'
        f'<span class="step-status {status_cls}">{label}</span>'
        f'</div>'
        f'<div class="step-desc">{html.escape(desc)}</div>'
        f'</div>'
    )


def draw_steps():
    """Redraw all four pipeline cards from session state (works live mid-run)."""
    for key, num, title, desc in STEPS:
        note = ss.step_notes.get(key, desc)
        placeholders[key].markdown(
            step_html(num, title, ss.step_states[key], note),
            unsafe_allow_html=True,
        )


def set_step(key: str, state: str, note: str | None = None):
    ss.step_states[key] = state
    if note is not None:
        ss.step_notes[key] = note
    draw_steps()


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">Multi-Agent AI System</div>
    <div class="hero-title"><span class="hero-white">Research</span><span class="hero-orange">Mind</span></div>
    <p class="hero-sub">
        Four specialized AI agents collaborate — searching, scraping, writing,
        and critiquing — to deliver a polished research report on any topic.
    </p>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)


# ── Layout: input left, pipeline right ───────────────────────────────────────
col_input, col_spacer, col_pipeline = st.columns([5, 0.5, 4])

with col_input:
    with st.container(key="input_box"):
        topic = st.text_input(
            "Research Topic",
            placeholder="e.g. Quantum computing breakthroughs in 2026",
            key="topic_input",
        )
        run_btn = st.button("⚡  Run Research Pipeline", use_container_width=True)

    chips = "".join(
        f'<span style="background:rgba(var(--surface),0.04);'
        f'border:1px solid rgba(var(--surface),0.1);border-radius:6px;'
        f'padding:0.25rem 0.7rem;font-size:0.75rem;color:var(--muted);'
        f'font-family:\'DM Sans\',sans-serif;">{ex}</span>'
        for ex in ["LLM agents 2026", "CRISPR gene editing", "Fusion energy progress"]
    )
    st.markdown(
        '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center;margin-bottom:1.5rem;">'
        '<span style="font-family:\'DM Mono\',monospace;font-size:0.68rem;'
        'color:var(--faint);letter-spacing:0.1em;">TRY →</span>'
        f'{chips}</div>',
        unsafe_allow_html=True,
    )

with col_pipeline:
    st.markdown('<div class="section-heading">Pipeline</div>', unsafe_allow_html=True)
    placeholders = {key: st.empty() for key, *_ in STEPS}

draw_steps()


# ── Run pipeline (live streaming from the LangGraph workflow) ────────────────
def run_pipeline(topic_val: str):
    ss.last_topic = topic_val
    ss.results = {}
    ss.step_notes = {}
    ss.step_states = {k: "waiting" for k, *_ in STEPS}
    ss.meta = {}
    ss.error = None
    ss.error_info = None

    initial_state = {
        "topic": topic_val,
        "search_results": "",
        "scraped_content": "",
        "report": "",
        "feedback": "",
        "score": 0,
    }

    started = time.time()
    drafts = 0
    score = 0
    current = "search"
    set_step("search", "running")

    try:
        # stream_mode="updates" yields {node_name: {state keys that node changed}}
        for chunk in graph.stream(initial_state, stream_mode="updates"):
            for node, update in chunk.items():
                if not update:
                    continue

                if node == "search":
                    ss.results["search"] = str(update.get("search_results", ""))
                    set_step("search", "done")
                    set_step("reader", "running")
                    current = "reader"

                elif node == "reader":
                    ss.results["reader"] = str(update.get("scraped_content", ""))
                    set_step("reader", "done")
                    set_step("writer", "running")
                    current = "writer"

                elif node == "writer":
                    drafts += 1
                    ss.results["writer"] = str(update.get("report", ""))
                    note = "Initial draft complete" if drafts == 1 else f"Revision {drafts - 1} complete"
                    set_step("writer", "done", note)
                    set_step("critic", "running", "Reviewing the draft…")
                    current = "critic"

                elif node == "critic":
                    score = int(update.get("score", 0) or 0)
                    ss.results["critic"] = str(update.get("feedback", ""))
                    verdict = "approved" if score >= PASS_SCORE else "needs a rewrite"
                    set_step("critic", "done", f"Score {score}/10 · {verdict}")
                    current = "critic"
                    if score < PASS_SCORE:
                        # The graph will loop back to the writer (unless the limit is hit)
                        set_step("writer", "running", f"Revising (critic scored {score}/10)…")
                        current = "writer"

        # Graph finished: settle every card in its final state
        for key in ("search", "reader", "writer", "critic"):
            ss.step_states[key] = "done"
        ss.step_notes["writer"] = f"{drafts} draft{'s' if drafts != 1 else ''} written"
        ss.step_notes["critic"] = f"Final score {score}/10"
        draw_steps()

        ss.meta = {
            "score": score,
            "drafts": drafts,
            "elapsed": time.time() - started,
        }

    except Exception as e:
        info = classify_error(e)
        set_step(current, "error", info["title"])
        ss.error_info = info
        ss.error = traceback.format_exc()


# Trigger: main button, or the "Try again" button from the error panel
action = ss.pending
ss.pending = None

if run_btn:
    if not topic.strip():
        st.warning("Please enter a research topic first.")
    else:
        run_pipeline(topic.strip())
elif action == "retry" and ss.last_topic:
    run_pipeline(ss.last_topic)


# ── Error panel ───────────────────────────────────────────────────────────────
if ss.error_info:
    info = ss.error_info
    st.markdown(
        '<div class="error-panel">'
        '<div class="error-eyebrow">⚠ Pipeline stopped</div>'
        f'<div class="error-title">{html.escape(info["title"])}</div>'
        f'<div class="error-msg">{html.escape(info["message"])}</div>'
        f'<div class="error-tip">💡 {html.escape(info["tip"])}</div>'
        '<p class="error-note">Trying again re-runs the whole pipeline for the same topic.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    btn_col, _ = st.columns([1, 2])
    with btn_col:
        st.button("↻  Try again", on_click=queue_retry, key="retry_btn", use_container_width=True)

    with st.expander("Error details"):
        st.code(ss.error)


# ── Results display ───────────────────────────────────────────────────────────
r = ss.results

if r:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Results</div>', unsafe_allow_html=True)

    meta = ss.meta
    if meta:
        score = meta["score"]
        score_cls = "good" if score >= PASS_SCORE else "warn"
        st.markdown(
            '<div class="chip-row">'
            f'<span class="chip {score_cls}">SCORE {score}/10</span>'
            f'<span class="chip">{meta["drafts"]} DRAFT{"S" if meta["drafts"] != 1 else ""}</span>'
            f'<span class="chip">{meta["elapsed"]:.0f}s</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Raw outputs in expanders
    if "search" in r:
        with st.expander("🔍 Search Results (raw)", expanded=False):
            st.markdown(
                '<div class="result-panel"><div class="result-panel-title">Search Agent Output</div>'
                f'<div class="result-content">{html.escape(r["search"])}</div></div>',
                unsafe_allow_html=True,
            )

    if "reader" in r:
        with st.expander("📄 Scraped Content (raw)", expanded=False):
            st.markdown(
                '<div class="result-panel"><div class="result-panel-title">Reader Agent Output</div>'
                f'<div class="result-content">{html.escape(r["reader"])}</div></div>',
                unsafe_allow_html=True,
            )

    # Final report
    if r.get("writer"):
        with st.container(key="report_box"):
            st.markdown(
                '<div class="panel-label orange">📝 Final Research Report</div>',
                unsafe_allow_html=True,
            )
            st.markdown(r["writer"])

        st.download_button(
            label="⬇  Download Report (.md)",
            data=r["writer"],
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
        )

    # Critic feedback
    if r.get("critic"):
        with st.container(key="feedback_box"):
            st.markdown(
                '<div class="panel-label green">🧐 Critic Feedback</div>',
                unsafe_allow_html=True,
            )
            st.markdown(r["critic"])


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="notice">
    ResearchMind · Powered by LangGraph multi-agent pipeline · Built with Streamlit
</div>
""", unsafe_allow_html=True)
