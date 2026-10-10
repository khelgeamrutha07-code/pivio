"""Shared Streamlit UI: design tokens, the ONE central stylesheet, page setup, auth gate and report rendering.

Design source: Stitch export "Executive Kinetic" (light SaaS, teal accent, Hanken Grotesk + Inter).
To restyle the app edit PALETTE and CSS_RULES below (and the matching hex values in .streamlit/config.toml).
"""
from __future__ import annotations
from core import auth, config, warmup
import html
import inspect
import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from core import auth, config, warmup

log = logging.getLogger("pivio")

LOGO = ""
LOGO_FILE = config.ROOT / "assets" / "logo.png"
FAVICON_FILE = config.ROOT / "assets" / "logo.png"# put your own image here to replace the tab icon

import streamlit as st


def _favicon():
    """The browser-tab icon: assets/logo.png if it exists, otherwise the LOGO emoji. Same on every page."""
    return str(FAVICON_FILE) if FAVICON_FILE.exists() else LOGO


TAGLINE = "Track every application, ace every interview."

# --------------------------------------------------------------------------- design tokens
# Single source of truth for colours. CSS reads them as --pv-* variables; Plotly reads them from here.
PALETTE: dict[str, str] = {
    "bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "subtle": "#F1F5F9",
    "border": "#CBD5E1",
    "border_strong": "#94A3B8",
    "text": "#0F172A",
    "muted": "#64748B",
    "faint": "#94A3B8",
    "primary": "#0D9488",
    "primary_hover": "#0F766E",
    "primary_active": "#115E59",
    "primary_tint": "#F0FDFA",
    "primary_border": "#99F6E4",
    "primary_text": "#115E59",
    "high": "#0D9488",
    "mid": "#D97706",
    "low": "#DC2626",
    "high_rgb": "13, 148, 136",
    "mid_rgb": "217, 119, 6",
    "low_rgb": "220, 38, 38",
    "accent": "#7C3AED",
    "accent_rgb": "124, 58, 237",
    "accent_tint": "#F5F3FF",
    "accent_border": "#DDD6FE",
    "white": "#FFFFFF",
}
FONT_BODY = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
FONT_HEAD = "'Hanken Grotesk', 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"

STATUS_CLASS = {"Applied": "applied", "Interview": "interview", "Offer": "offer", "Rejected": "rejected"}
PACE_TARGET = (130, 150)  # words per minute, from the design's "Speaking pace" card

CSS_RULES = """
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');
/* ---------- base ---------- */
.stApp,[data-testid="stAppViewContainer"]{background:var(--pv-bg);color:var(--pv-text);}
.stApp,.stApp p,.stApp li,.stApp label,.stApp input,.stApp textarea,.stApp button,.stApp [data-baseweb],.stApp [data-testid="stMarkdownContainer"]{font-family:var(--pv-font-body);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stAppDeployButton"],[data-testid="stDeployButton"],footer{display:none !important;}
[data-testid="stMainBlockContainer"],.block-container{max-width:1280px;padding:2rem 2rem 3rem 2rem;}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:var(--pv-font-head);color:var(--pv-text);letter-spacing:-.02em;}
.stApp h1{font-size:2rem;font-weight:700;line-height:2.5rem;}
.stApp h2{font-size:1.375rem;font-weight:600;line-height:1.75rem;}
.stApp h3{font-size:1.125rem;font-weight:600;line-height:1.5rem;}
[data-testid="stCaptionContainer"]{color:var(--pv-muted);}
hr{border-color:var(--pv-border);}
/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{background:var(--pv-surface);border-right:1px solid var(--pv-border);}
[data-testid="stSidebarNav"]::before{content:"Pivio";display:block;font-family:var(--pv-font-head);font-weight:700;font-size:1.5rem;letter-spacing:-.02em;color:var(--pv-text);padding:1.25rem 1rem .5rem 1rem;}
[data-testid="stSidebarNavLink"]{border-radius:8px;border:1px solid transparent;color:var(--pv-muted);font-weight:500;}
[data-testid="stSidebarNavLink"]:hover{background:var(--pv-subtle);color:var(--pv-text);}
[data-testid="stSidebarNavLink"][aria-current="page"]{background:var(--pv-primary-tint);border-color:var(--pv-primary-border);color:var(--pv-primary-text);font-weight:600;}
[data-testid="stSidebarNav"] li:first-child [data-testid="stSidebarNavLink"] span,[data-testid="stSidebarNav"] li:first-child [data-testid="stSidebarNavLink"] p{font-size:0 !important;}
[data-testid="stSidebarNav"] li:first-child [data-testid="stSidebarNavLink"]::after{content:"Dashboard";font-size:.9rem;}
[data-testid="stSidebarUserContent"]{border-top:1px solid var(--pv-border);}
.pv-user{display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;min-width:0;}
.pv-avatar{flex:none;width:28px;height:28px;border-radius:9999px;background:var(--pv-primary);color:var(--pv-white);display:inline-flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:600;}
.pv-user-email{font-size:.8rem;color:var(--pv-muted);font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
/* ---------- buttons ---------- */
button[data-testid^="stBaseButton-primary"]{background:var(--pv-primary);border:1px solid var(--pv-primary);border-radius:8px;font-weight:600;box-shadow:none;}
button[data-testid^="stBaseButton-primary"],button[data-testid^="stBaseButton-primary"] p{color:var(--pv-white);}
button[data-testid^="stBaseButton-primary"]:hover:not(:disabled){background:var(--pv-primary-hover);border-color:var(--pv-primary-hover);}
button[data-testid^="stBaseButton-primary"]:active:not(:disabled){background:var(--pv-primary-active);border-color:var(--pv-primary-active);}
button[data-testid^="stBaseButton-secondary"],a[data-testid^="stBaseLinkButton"]{background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:8px;font-weight:600;box-shadow:none;}
button[data-testid^="stBaseButton-secondary"],button[data-testid^="stBaseButton-secondary"] p,a[data-testid^="stBaseLinkButton"],a[data-testid^="stBaseLinkButton"] p{color:var(--pv-text);}
button[data-testid^="stBaseButton-secondary"]:hover:not(:disabled),a[data-testid^="stBaseLinkButton"]:hover{background:var(--pv-bg);border-color:var(--pv-border-strong);}
button[data-testid^="stBaseButton-tertiary"]{border-radius:8px;color:var(--pv-muted);}
button[data-testid^="stBaseButton-tertiary"]:hover{background:var(--pv-subtle);color:var(--pv-text);}
button:disabled{opacity:.5;cursor:not-allowed;}
a[data-testid="stPageLink-NavLink"]{border-radius:8px;font-weight:600;color:var(--pv-primary);}
a[data-testid="stPageLink-NavLink"]:hover{background:var(--pv-primary-tint);}
/* ---------- inputs ---------- */
div[data-baseweb="input"],div[data-baseweb="textarea"],div[data-baseweb="select"] > div:first-child{background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:8px;}
div[data-baseweb="input"]:focus-within,div[data-baseweb="textarea"]:focus-within,div[data-baseweb="select"] > div:first-child:focus-within{border-color:var(--pv-primary);box-shadow:0 0 0 3px rgba(var(--pv-high-rgb),.15);}
div[data-baseweb="input"] input,div[data-baseweb="textarea"] textarea{color:var(--pv-text);}
input::placeholder,textarea::placeholder{color:var(--pv-faint);}
[data-testid="stFileUploaderDropzone"]{background:var(--pv-surface);border:1.5px dashed var(--pv-border-strong);border-radius:12px;}
[data-testid="stForm"]{border:none;padding:0;background:transparent;}
div[data-testid="stRadio"] div[role="radiogroup"]{gap:.75rem;}
div[data-testid="stRadio"] label[data-baseweb="radio"]{background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:12px;padding:.75rem 1rem;margin:0;}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover{border-color:var(--pv-border-strong);}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked){border-color:var(--pv-primary);background:var(--pv-primary-tint);box-shadow:0 0 0 3px rgba(var(--pv-high-rgb),.15);}
/* ---------- tabs, expanders, alerts, chat ---------- */
button[data-baseweb="tab"]{font-weight:600;color:var(--pv-muted);}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--pv-primary);}
[data-baseweb="tab-highlight"]{background-color:var(--pv-primary);}
[data-baseweb="tab-border"]{background-color:var(--pv-border);}
[data-testid="stExpander"] details{background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:12px;}
[data-testid="stExpander"] summary{font-weight:600;}
[data-testid="stAlert"]{border-radius:12px;}
[data-testid="stChatMessage"]{background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:12px;padding:.9rem 1rem;margin-bottom:.75rem;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]){background:var(--pv-primary-tint);border-color:var(--pv-primary-border);}
/* ---------- cards: st.container(border=True) and st.metric ---------- */
[data-testid="stVerticalBlockBorderWrapper"]{background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:12px;box-shadow:0 1px 3px 0 rgba(15,23,42,.06);}
[data-testid="stMetric"]{background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:12px;padding:1rem 1.25rem;box-shadow:0 1px 2px 0 rgba(15,23,42,.04);}
[data-testid="stMetricLabel"]{color:var(--pv-muted);}
[data-testid="stMetricValue"]{font-family:var(--pv-font-head);font-weight:700;font-variant-numeric:tabular-nums;color:var(--pv-text);}
.element-container:has(.pv-marker),[data-testid="stElementContainer"]:has(.pv-marker),.element-container:has(style),[data-testid="stElementContainer"]:has(style){display:none;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.pv-marker-hero){border:2px solid var(--pv-primary);background:linear-gradient(135deg,var(--pv-surface) 0%,var(--pv-primary-tint) 100%);}
[data-testid="stVerticalBlockBorderWrapper"]:has(.pv-marker-callout){background:var(--pv-accent-tint);border:1px solid var(--pv-accent-border);border-left:3px solid var(--pv-accent);}
[data-testid="stVerticalBlockBorderWrapper"]:has(.pv-marker-danger){background:rgba(var(--pv-low-rgb),.04);border:1px solid rgba(var(--pv-low-rgb),.35);}
/* ---------- custom snippets ---------- */
.pv-eyebrow{font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--pv-muted);}
.pv-card-title{font-family:var(--pv-font-head);font-size:1.0625rem;font-weight:700;color:var(--pv-text);margin:0;}
.pv-card-sub{font-size:.8rem;color:var(--pv-muted);margin:.15rem 0 .75rem 0;}
.pv-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.75rem;}
.pv-pill{display:inline-block;padding:2px 10px;border-radius:9999px;font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;border:1px solid transparent;white-space:nowrap;font-variant-numeric:tabular-nums;}
.pv-chip{display:inline-block;padding:2px 8px;border-radius:6px;font-size:.75rem;font-weight:600;background:var(--pv-subtle);color:var(--pv-muted);border:1px solid var(--pv-border);white-space:nowrap;}
.pv-tier-high{background:rgba(var(--pv-high-rgb),.08);color:var(--pv-high);border-color:rgba(var(--pv-high-rgb),.25);}
.pv-tier-mid{background:rgba(var(--pv-mid-rgb),.08);color:var(--pv-mid);border-color:rgba(var(--pv-mid-rgb),.25);}
.pv-tier-low{background:rgba(var(--pv-low-rgb),.08);color:var(--pv-low);border-color:rgba(var(--pv-low-rgb),.25);}
.pv-st-applied{background:var(--pv-subtle);color:var(--pv-muted);border-color:var(--pv-border);}
.pv-st-interview{background:rgba(var(--pv-accent-rgb),.08);color:var(--pv-accent);border-color:rgba(var(--pv-accent-rgb),.25);}
.pv-st-offer{background:rgba(var(--pv-high-rgb),.08);color:var(--pv-high);border-color:rgba(var(--pv-high-rgb),.25);}
.pv-st-rejected{background:rgba(var(--pv-low-rgb),.08);color:var(--pv-low);border-color:rgba(var(--pv-low-rgb),.25);}
.pv-score{font-family:var(--pv-font-head);font-size:3.5rem;font-weight:800;line-height:1;letter-spacing:-.02em;font-variant-numeric:tabular-nums;}
.pv-score-den{font-size:1.5rem;font-weight:700;color:var(--pv-faint);margin-left:.4rem;}
.pv-score-high{color:var(--pv-high);} .pv-score-mid{color:var(--pv-mid);} .pv-score-low{color:var(--pv-low);}
.pv-legend{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem 1rem;background:var(--pv-surface);border:1px solid var(--pv-border);border-radius:12px;padding:.6rem 1rem;font-size:.8rem;color:var(--pv-muted);font-weight:500;margin-bottom:1rem;}
.pv-bar-row{margin-bottom:.9rem;}
.pv-bar-top{display:flex;justify-content:space-between;align-items:center;gap:.5rem;font-size:.8rem;font-weight:600;color:var(--pv-text);margin-bottom:.35rem;}
.pv-bar-track{height:10px;background:var(--pv-subtle);border-radius:9999px;overflow:hidden;}
.pv-bar-fill{height:100%;border-radius:9999px;}
.pv-fill-high{background:var(--pv-high);} .pv-fill-mid{background:var(--pv-mid);} .pv-fill-low{background:var(--pv-low);}
.pv-list{list-style:none;margin:0;padding:0;}
.pv-list li{position:relative;padding:.5rem .5rem .5rem 1.75rem;font-size:.88rem;color:var(--pv-text);border-bottom:1px solid var(--pv-border);}
.pv-list li:last-child{border-bottom:none;}
.pv-list li::before{position:absolute;left:.25rem;top:.5rem;font-weight:700;}
.pv-list-ok li::before{content:"✓";color:var(--pv-high);}
.pv-list-warn li::before{content:"!";color:var(--pv-mid);}
.pv-quote{margin:0;font-style:italic;color:var(--pv-text);font-size:.9rem;line-height:1.5;}
.pv-body{font-size:.88rem;color:var(--pv-text);line-height:1.5;margin:.5rem 0 0 0;}
.pv-row{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem 1rem;padding:.75rem 1rem;border-bottom:1px solid var(--pv-border);}
.pv-row:last-child{border-bottom:none;}
.pv-row:hover{background:var(--pv-bg);}
.pv-row-main{flex:1 1 220px;min-width:0;}
.pv-row-title{font-weight:600;color:var(--pv-text);}
.pv-row-meta{font-size:.8rem;color:var(--pv-muted);}
.pv-step-n{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:8px;background:var(--pv-primary-tint);color:var(--pv-primary-text);border:1px solid var(--pv-primary-border);font-weight:700;font-size:.8rem;}
.pv-step-title{font-family:var(--pv-font-head);font-weight:700;margin:.5rem 0 .15rem 0;color:var(--pv-text);}
.pv-step-body{font-size:.85rem;color:var(--pv-muted);margin:0;}
.pv-qhead{display:flex;align-items:center;justify-content:space-between;gap:.75rem;}
.pv-qtag{display:inline-block;padding:1px 8px;border-radius:6px;background:var(--pv-subtle);border:1px solid var(--pv-border);font-size:.72rem;font-weight:700;color:var(--pv-muted);margin-right:.5rem;}
.pv-qtext{font-weight:600;font-size:.92rem;color:var(--pv-text);}
.pv-brand-login{font-family:var(--pv-font-head);font-weight:800;font-size:2rem;letter-spacing:-.02em;color:var(--pv-text);margin:0;}
.pv-tagline{color:var(--pv-muted);font-size:.9rem;margin:.15rem 0 1rem 0;}
.pv-muted{color:var(--pv-muted);font-size:.85rem;}
/* ---------- always-visible borders (override Streamlit defaults) ---------- */
div[data-baseweb="input"],div[data-baseweb="textarea"],div[data-baseweb="select"] > div:first-child{border:1px solid var(--pv-border-strong) !important;border-radius:8px !important;background:var(--pv-surface) !important;}
div[data-baseweb="base-input"]{border:none !important;background:transparent !important;}
div[data-baseweb="input"]:focus-within,div[data-baseweb="textarea"]:focus-within,div[data-baseweb="select"] > div:first-child:focus-within{border-color:var(--pv-primary) !important;}
[data-testid="stVerticalBlockBorderWrapper"]{border:1px solid var(--pv-border-strong) !important;border-radius:12px !important;background:var(--pv-surface) !important;}
[data-testid="stMetric"]{border:1px solid var(--pv-border-strong) !important;}
[data-testid="stExpander"] details{border:1px solid var(--pv-border-strong) !important;}
button[data-testid^="stBaseButton-secondary"]{border:1px solid var(--pv-border-strong) !important;}
"""

HIDE_INPUT_HINT_CSS = """
[data-testid="InputInstructions"]{display:none !important;}
[data-testid="stStatusWidget"]{display:none !important;}
"""

HIDE_SIDEBAR_CSS = """
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stExpandSidebarButton"]{display:none !important;}
"""


def _css_variables() -> str:
    pairs = [f"--pv-{k.replace('_', '-')}:{v};" for k, v in PALETTE.items()]
    pairs.append(f"--pv-font-body:{FONT_BODY};--pv-font-head:{FONT_HEAD};")
    return ":root{" + "".join(pairs) + "}"


def _compact(css: str) -> str:
    """Drop blank lines: a blank line would end the HTML block and Markdown would mangle the rest."""
    return "\n".join(line.strip() for line in css.splitlines() if line.strip())


def _style_tag(extra: str = "") -> str:
    extra = extra + "\n" + HIDE_INPUT_HINT_CSS
    # @import must be the first rule of the stylesheet, so variables go after the first line.
    first, _, rest = CSS_RULES.strip().partition("\n")
    return "<style>\n" + _compact("\n".join([first, _css_variables(), rest, extra])) + "\n</style>"


# --------------------------------------------------------------------------- small helpers
def _t(value: object) -> str:
    """Escape user/LLM text for use inside our HTML snippets; collapses whitespace (blank lines break Markdown HTML)."""
    return html.escape(" ".join(str(value if value is not None else "").split()))


def tier(score: float | int | None) -> tuple[str, str]:
    """Design score tiers: >=7 high / strong pass, 5-6.9 mid / needs work, <5 low / unprepared."""
    s = float(score or 0)
    if s >= 7:
        return "high", "Strong pass"
    if s >= 5:
        return "mid", "Needs work"
    return "low", "Unprepared"


def score_pill(score: float | int | None, with_label: bool = False) -> str:
    """Coloured ``8.8 / 10`` pill (optionally followed by the tier label)."""
    tone, label = tier(score)
    text = f"{float(score or 0):.1f} / 10" + (f" · {label}" if with_label else "")
    return f'<span class="pv-pill pv-tier-{tone}">{_t(text)}</span>'


def badge(status: str) -> str:
    """HTML status badge for an application status."""
    cls = STATUS_CLASS.get(status, "applied")
    return f'<span class="pv-pill pv-st-{cls}">{_t(status)}</span>'


def chip(text: str) -> str:
    return f'<span class="pv-chip">{_t(text)}</span>'


def marker(name: str) -> None:
    """Invisible hook so CSS can style the enclosing bordered container (hero / callout / danger)."""
    st.markdown(f'<span class="pv-marker pv-marker-{name}"></span>', unsafe_allow_html=True)


def card_head(title: str, subtitle: str = "", right: str = "") -> None:
    sub = f'<p class="pv-card-sub">{_t(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f'<div class="pv-head"><div><p class="pv-card-title">{_t(title)}</p>{sub}</div>{right}</div>',
        unsafe_allow_html=True,
    )


def app_row(a: dict) -> str:
    """One hairline-divided application row (used on the dashboard and the applications page)."""
    meta = f"Resume used: {a.get('resume_label') or '—'} · Applied {a.get('applied_on', '')}"
    return (
        f'<div class="pv-row"><div class="pv-row-main"><div class="pv-row-title">{_t(a.get("company"))} — {_t(a.get("role"))}</div>'
        f'<div class="pv-row-meta">{_t(meta)}</div></div>{badge(a.get("status", ""))}</div>'
    )


def show_error(message: str) -> None:
    """Friendly error banner (never a traceback)."""
    st.error(message, icon=":material/error:")


def show_unexpected(action: str, exc: BaseException | None = None) -> None:
    """Friendly banner for an unexpected failure; the technical detail goes to the server log only."""
    log.error("Unexpected error while trying to %s", action, exc_info=exc)
    show_error(f"Something went wrong while trying to {action}. Please try again. "
               "If it keeps happening, check your internet connection and your API keys.")


def flash(message: str, icon: str = "✅") -> None:
    """Queue a toast that survives the next st.rerun()."""
    st.session_state["_flash"] = (icon, message)


def _plotly_stretch_kwargs() -> dict:
    """``width="stretch"`` on new Streamlit, ``use_container_width=True`` on older ones."""
    try:
        if "width" in inspect.signature(st.plotly_chart).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


def plotly(fig, key: str) -> None:
    """Render a Plotly figure full width with the Pivio styling."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin={"l": 8, "r": 8, "t": 16, "b": 8}, height=300,
        font={"family": FONT_BODY, "color": PALETTE["muted"], "size": 12},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        colorway=[PALETTE["primary"], PALETTE["accent"], PALETTE["mid"], PALETTE["muted"], PALETTE["low"]],
    )
    fig.update_xaxes(showgrid=False, linecolor=PALETTE["border"], tickfont={"color": PALETTE["text"]})
    fig.update_yaxes(gridcolor=PALETTE["border"], zeroline=False)
    st.plotly_chart(fig, key=key, **_plotly_stretch_kwargs())


# --------------------------------------------------------------------------- auth + page shell
def _auth_form() -> None:
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid, st.container(border=True):
        st.markdown('<p class="pv-brand-login">Pivio</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="pv-tagline">{_t(TAGLINE)}</p>', unsafe_allow_html=True)
        tab_in, tab_up = st.tabs(["Log in", "Sign up"])
        with tab_in:
            with st.form("login_form"):
                email = st.text_input("Email", key="li_email")
                pw = st.text_input("Password", type="password", key="li_pw")
                submitted = st.form_submit_button("Log in", type="primary")
            if submitted:
                _handle_login(email, pw)
        with tab_up:
            with st.form("signup_form"):
                email_new = st.text_input("Email", key="su_email")
                pw_new = st.text_input("Password (min 6 characters)", type="password", key="su_pw")
                created = st.form_submit_button("Create account", type="primary")
            if created:
                _handle_signup(email_new, pw_new)
        st.caption("🔒 Pivio stores your resumes' extracted text, applications and interview transcripts in your private "
                   "account. See Settings after logging in for details.")


def _handle_login(email: str, pw: str) -> None:
    ok = False
    try:
        with st.spinner("Logging in..."):
            auth.sign_in(email, pw)
        ok = True
    except auth.AuthError as exc:
        show_error(str(exc))
    if ok:
        st.rerun()


def _handle_signup(email: str, pw: str) -> None:
    msg, ok = "", False
    try:
        with st.spinner("Creating account..."):
            msg = auth.sign_up(email, pw)
        ok = True
    except auth.AuthError as exc:
        show_error(str(exc))
    
    if ok:
        if auth.current_user():
            st.rerun()
        st.success("Account created successfully!")
        st.info(
               "📩 Please check your email inbox for the verification link. "
               "If you don't see it, check your spam or junk folder. "
                "Verify your email before logging in."
              )



def _sidebar(user: dict) -> None:
    with st.sidebar:
        email = str(user.get("email") or "")
        initials = _t((email[:2] or "?").upper())
        st.markdown(
            f'<div class="pv-user"><span class="pv-avatar">{initials}</span><span class="pv-user-email" title="{_t(email)}">{_t(email)}</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("Log out", key="logout_btn", icon=":material/logout:"):
            auth.sign_out()
            st.rerun()


def setup_page(title: str, icon: str = LOGO, require_login: bool = True) -> None:
    """Call first on every page: config, styling, sidebar and auth gate."""
    st.set_page_config(page_title=f"{title} · Pivio", page_icon="assets/logo.png", layout="wide", initial_sidebar_state="expanded")

    if LOGO_FILE.exists():
        st.logo(str(LOGO_FILE), size="large")
    user = auth.current_user()
    st.markdown(_style_tag("" if user else _compact(HIDE_SIDEBAR_CSS)), unsafe_allow_html=True)
    missing = config.missing_settings()
    if user:
        warmup.start()
        _sidebar(user)
        pending = st.session_state.pop("_flash", None)
        if pending:
            st.toast(pending[1], icon=pending[0])
    if missing:
        show_error("Setup incomplete. Missing configuration: " + ", ".join(missing) + ". See README.")
        st.stop()
    if require_login and not user:
        _auth_form()
        st.stop()


# --------------------------------------------------------------------------- report
def _legend() -> None:
    st.markdown(
        '<div class="pv-legend"><span>Performance scoring scale:</span>'
        '<span class="pv-pill pv-tier-high">≥ 7.0 Strong pass</span>'
        '<span class="pv-pill pv-tier-mid">5.0 – 6.9 Needs work</span>'
        '<span class="pv-pill pv-tier-low">&lt; 5.0 Unprepared</span></div>',
        unsafe_allow_html=True,
    )


def _skill_bars(skills: dict) -> str:
    rows = []
    for name, value in skills.items():
        v = max(0.0, min(10.0, float(value or 0)))
        tone, _ = tier(v)
        rows.append(
            f'<div class="pv-bar-row"><div class="pv-bar-top"><span>{_t(name)}</span>{score_pill(v)}</div>'
            f'<div class="pv-bar-track"><div class="pv-bar-fill pv-fill-{tone}" style="width:{v * 10:.0f}%"></div></div></div>'
        )
    return "".join(rows)


def _bullets(items: list, kind: str) -> str:
    return f'<ul class="pv-list pv-list-{kind}">' + "".join(f"<li>{_t(i)}</li>" for i in items) + "</ul>"


def _pace_hint(wpm: float | None) -> str:
    if not wpm:
        return "Record a voice answer to measure your pace."
    lo, hi = PACE_TARGET
    verdict = "In the ideal range" if lo <= wpm <= hi else ("A little slow" if wpm < lo else "A little fast")
    return f"Target {lo}–{hi} wpm · {verdict}"


def _criteria_chart(crit: dict, key: str) -> None:
    df = pd.DataFrame({"Criterion": [k.title() for k in crit], "Score": [float(v) for v in crit.values()]})
    fig = px.bar(df, x="Criterion", y="Score", range_y=[0, 10])
    fig.update_traces(marker_color=[PALETTE[tier(s)[0]] for s in df["Score"]], texttemplate="%{y:.1f}",
                      textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f}<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title=None, bargap=0.45)
    plotly(fig, key)


def render_report(report: dict, transcript: list[dict], evaluations: list[dict],
                  key_prefix: str = "rep", expand_details: bool = False) -> None:
    """Render a full feedback report (used after an interview and on the History page)."""
    delivery = report.get("delivery") or {}
    overall = float(report.get("overall_score") or 0)
    tone, label = tier(overall)
    _legend()

    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        marker("hero")
        card_head("Overall interview rating", f"Average across {len(transcript) or 'all'} answered questions",
                  f'<span class="pv-pill pv-tier-{tone}">{_t(label)}</span>')
        st.markdown(f'<div class="pv-score pv-score-{tone}">{overall:.1f}<span class="pv-score-den">/ 10.0</span></div>',
                    unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m1.metric("Filler words", delivery.get("filler_total", 0))
        fillers = delivery.get("fillers") or {}
        m1.caption(", ".join(f"{v}× “{k}”" for k, v in list(fillers.items())[:3]) or "None detected")
        wpm = delivery.get("avg_wpm")
        m2.metric("Speaking pace (wpm)", f"{wpm:.0f}" if wpm else "n/a")
        m2.caption(_pace_hint(wpm))
    with right, st.container(border=True):
        card_head("Score by key skill", "Skills and topics assessed in this interview")
        skills = report.get("per_skill_scores") or {}
        if skills:
            st.markdown(_skill_bars(skills), unsafe_allow_html=True)
        else:
            st.caption("No skill breakdown available.")

    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        card_head("Competency score breakdown", "Average of the evaluator's four criteria (0–10)")
        crit = report.get("criteria_averages") or {}
        if crit:
            _criteria_chart(crit, f"{key_prefix}_criteria")
        else:
            st.caption("No criteria scores available.")
    with right, st.container(border=True):
        card_head("Speech & delivery", "How your answers sounded")
        d1, d2 = st.columns(2)
        d1.metric("Avg answer length (words)", delivery.get("avg_words", 0))
        d2.metric("Answers", delivery.get("answers", 0))
        if fillers:
            st.markdown(" ".join(chip(f"{k} ×{v}") for k, v in fillers.items()), unsafe_allow_html=True)
        else:
            st.caption("No filler words detected.")

    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        card_head("Key strengths", right=f'<span class="pv-pill pv-tier-high">{len(report.get("strengths") or [])} highlights</span>')
        st.markdown(_bullets(report.get("strengths") or ["No strengths recorded."], "ok"), unsafe_allow_html=True)
    with right, st.container(border=True):
        card_head("Areas for focused improvement", right='<span class="pv-pill pv-tier-mid">Actionable</span>')
        st.markdown(_bullets(report.get("weaknesses") or ["No weaknesses recorded."], "warn"), unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        card_head("Best answer", right='<span class="pv-pill pv-tier-high">Best</span>')
        st.markdown(f'<p class="pv-body">{_t(report.get("best_answer", ""))}</p>', unsafe_allow_html=True)
    with right, st.container(border=True):
        card_head("Weakest answer", right='<span class="pv-pill pv-tier-mid">Needs work</span>')
        st.markdown(f'<p class="pv-body">{_t(report.get("weakest_answer", ""))}</p>', unsafe_allow_html=True)
    with st.container(border=True):
        marker("callout")
        card_head("Improved sample answer", "A stronger way to answer your weakest question")
        st.markdown(f'<p class="pv-quote">“{_t(report.get("improved_answer_for_weakest", ""))}”</p>', unsafe_allow_html=True)

    tips = report.get("tips") or []
    if tips:
        st.subheader("Action plan")
        for start in range(0, len(tips), 3):
            cols = st.columns(3, gap="large")
            for offset, tip in enumerate(tips[start:start + 3]):
                with cols[offset], st.container(border=True):
                    st.markdown(
                        f'<span class="pv-step-n">{start + offset + 1}</span><p class="pv-step-body" style="margin-top:.6rem">{_t(tip)}</p>',
                        unsafe_allow_html=True,
                    )

    scores = report.get("turn_scores") or []
    avg_txt = f" · average {sum(scores) / len(scores):.1f} / 10" if scores else ""
    with st.expander(f"Question-by-question detailed evaluation ({len(transcript)}){avg_txt}", expanded=expand_details):
        for t, e in zip(transcript, evaluations, strict=False):
            parts = [e.get(k, 0) for k in ("relevance", "depth", "structure", "clarity")]
            avg = sum(parts) / 4
            follow = " (follow-up)" if t.get("is_followup") else ""
            with st.container(border=True):
                st.markdown(
                    f'<div class="pv-qhead"><div><span class="pv-qtag">Q{_t(t.get("turn"))}{follow}</span>'
                    f'<span class="pv-qtext">{_t(t.get("question"))}</span></div>{score_pill(avg)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f'<p class="pv-body"><b>Your answer:</b> {_t(t.get("answer"))}</p>', unsafe_allow_html=True)
                st.markdown(
                    " ".join(chip(f"{k} {e.get(k, 0)}") for k in ("relevance", "depth", "structure", "clarity")),
                    unsafe_allow_html=True,
                )
                if e.get("reason"):
                    st.caption(str(e["reason"]))
