"""Shared UI theme for the Streamlit app — palette, chart defaults, formatters.

Single source of truth for the fintech premium look & feel. All pages must
use these constants/helpers instead of hardcoding colors or chart layouts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

import plotly.graph_objects as go
import streamlit as st


# ── Palette ────────────────────────────────────────────────────────────
# Refined institutional fintech tones (less saturated than raw Material).
# Inspired by Stripe, Linear, Wealthfront.

BG_DEEP: Final = "#070E1A"
BG_BASE: Final = "#0A1424"
BG_ELEVATED: Final = "#111D32"
BG_OVERLAY: Final = "rgba(17, 29, 50, 0.55)"

BORDER_SOFT: Final = "rgba(148, 163, 184, 0.08)"
BORDER_ACCENT: Final = "rgba(59, 130, 246, 0.18)"

TEXT_PRIMARY: Final = "#E2E8F0"
TEXT_MUTED: Final = "#94A3B8"
TEXT_FAINT: Final = "#64748B"

# Brand — a slightly desaturated electric blue (Linear-style)
BRAND: Final = "#3B82F6"
BRAND_HOVER: Final = "#60A5FA"

# P&L — institutional emerald/rose, not Material green/red
POSITIVE: Final = "#10B981"
NEGATIVE: Final = "#F43F5E"
NEUTRAL: Final = "#64748B"

# Chart categorical palette — 8 tones, harmonious
CHART_PALETTE: Final = (
    "#3B82F6",  # blue
    "#06B6D4",  # cyan
    "#10B981",  # emerald
    "#F43F5E",  # rose
    "#F59E0B",  # amber
    "#A855F7",  # violet
    "#14B8A6",  # teal
    "#EC4899",  # pink
)


# ── CSS ────────────────────────────────────────────────────────────────

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
}}

/* Radial-gradient background so glassmorphism has something to blur */
.stApp {{
    background:
        radial-gradient(ellipse 80% 50% at 20% 0%, rgba(59, 130, 246, 0.08), transparent 70%),
        radial-gradient(ellipse 60% 40% at 90% 20%, rgba(168, 85, 247, 0.05), transparent 70%),
        {BG_DEEP};
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {BG_BASE} 0%, {BG_DEEP} 100%);
    border-right: 1px solid {BORDER_SOFT};
}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {{
    font-size: 1.1rem;
    letter-spacing: 0.02em;
    color: {TEXT_PRIMARY};
}}

/* Tabular numbers everywhere — critical for financial UIs */
div[data-testid="stMetricValue"],
div[data-testid="stMetricDelta"],
div[data-testid="stDataFrame"],
td, th,
code {{
    font-variant-numeric: tabular-nums;
    font-feature-settings: 'tnum' 1;
}}

/* Metric cards — premium glassmorphism */
div[data-testid="stMetric"] {{
    background: {BG_OVERLAY};
    backdrop-filter: blur(14px) saturate(140%);
    -webkit-backdrop-filter: blur(14px) saturate(140%);
    border: 1px solid {BORDER_SOFT};
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px -12px rgba(0,0,0,0.5);
    transition: border-color 0.2s ease, transform 0.2s ease;
}}
div[data-testid="stMetric"]:hover {{
    border-color: {BORDER_ACCENT};
    transform: translateY(-1px);
}}
div[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED} !important;
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
div[data-testid="stMetricValue"] {{
    font-size: 1.7rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: {TEXT_PRIMARY};
}}

/* P&L colors — refined */
div[data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Up"] {{ fill: {POSITIVE}; }}
div[data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Down"] {{ fill: {NEGATIVE}; }}
[data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Up"]) {{ color: {POSITIVE}; font-weight: 600; }}
[data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Down"]) {{ color: {NEGATIVE}; font-weight: 600; }}

/* Page titles — custom typographic treatment via .app-header */
h1 {{
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: {TEXT_PRIMARY} !important;
}}
h2, h3 {{
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    color: {TEXT_PRIMARY} !important;
}}

.app-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0 20px 0;
    border-bottom: 1px solid {BORDER_SOFT};
    margin-bottom: 24px;
}}
.app-header-title {{
    display: flex;
    flex-direction: column;
    gap: 4px;
}}
.app-header-title .eyebrow {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {TEXT_FAINT};
    font-weight: 500;
}}
.app-header-title h1 {{
    font-size: 1.9rem !important;
    margin: 0 !important;
    line-height: 1.1 !important;
}}
.app-header-meta {{
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.82rem;
    color: {TEXT_MUTED};
}}
.status-dot {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 5px 10px;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    color: {POSITIVE};
}}
.status-dot::before {{
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {POSITIVE};
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.18);
    animation: pulse 2s ease-in-out infinite;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.6; }}
}}

/* Section headers — alternative to <hr> */
.section-title {{
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {TEXT_MUTED};
    font-weight: 600;
    margin: 28px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid {BORDER_SOFT};
}}

/* Buttons — primary (brand) */
button[kind="primary"], .stButton > button[kind="primary"] {{
    background: linear-gradient(180deg, {BRAND} 0%, #2563EB 100%);
    border: 1px solid rgba(59, 130, 246, 0.4);
    border-radius: 10px;
    font-weight: 500;
    box-shadow: 0 1px 0 rgba(255,255,255,0.15) inset, 0 4px 12px -4px rgba(59, 130, 246, 0.5);
    transition: all 0.2s ease;
}}
button[kind="primary"]:hover {{
    background: linear-gradient(180deg, {BRAND_HOVER} 0%, {BRAND} 100%);
    transform: translateY(-1px);
    box-shadow: 0 1px 0 rgba(255,255,255,0.2) inset, 0 6px 16px -4px rgba(59, 130, 246, 0.6);
}}

/* Secondary buttons — chip style (used for AI suggestions) */
.stButton > button:not([kind="primary"]) {{
    background: rgba(148, 163, 184, 0.06);
    border: 1px solid {BORDER_SOFT};
    border-radius: 999px;
    color: {TEXT_PRIMARY};
    font-weight: 500;
    font-size: 0.85rem;
    padding: 6px 14px;
    transition: all 0.15s ease;
}}
.stButton > button:not([kind="primary"]):hover {{
    background: rgba(59, 130, 246, 0.08);
    border-color: {BORDER_ACCENT};
    color: {BRAND_HOVER};
}}

/* Dataframes */
div[data-testid="stDataFrame"] {{
    background: {BG_OVERLAY};
    backdrop-filter: blur(10px);
    border-radius: 12px;
    border: 1px solid {BORDER_SOFT};
    overflow: hidden;
}}
div[data-testid="stDataFrame"] thead th {{
    background: rgba(17, 29, 50, 0.9) !important;
    color: {TEXT_MUTED} !important;
    text-transform: uppercase;
    font-size: 0.72rem !important;
    letter-spacing: 0.05em;
    font-weight: 600 !important;
    border-bottom: 1px solid {BORDER_SOFT} !important;
}}
div[data-testid="stDataFrame"] tbody tr:hover {{
    background: rgba(59, 130, 246, 0.04) !important;
}}

/* Tabs */
button[data-baseweb="tab"] {{
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    color: {TEXT_MUTED};
    letter-spacing: 0.01em;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {TEXT_PRIMARY} !important;
}}
div[data-baseweb="tab-highlight"] {{
    background: {BRAND} !important;
    height: 2px !important;
    border-radius: 2px;
}}

/* Expander */
details {{
    background: {BG_OVERLAY};
    border: 1px solid {BORDER_SOFT};
    border-radius: 10px;
    backdrop-filter: blur(10px);
}}

/* Chat messages */
[data-testid="stChatMessage"] {{
    background: {BG_OVERLAY};
    backdrop-filter: blur(10px);
    border: 1px solid {BORDER_SOFT};
    border-radius: 14px;
    padding: 14px 18px;
}}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-baseweb="select"] > div {{
    background: rgba(10, 20, 36, 0.6) !important;
    border: 1px solid {BORDER_SOFT} !important;
    border-radius: 8px !important;
    color: {TEXT_PRIMARY} !important;
    transition: border-color 0.15s ease;
}}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus {{
    border-color: {BRAND} !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}}

/* Remove default divider visual clutter — use margin instead */
hr {{
    border-color: {BORDER_SOFT} !important;
    margin: 28px 0 !important;
    opacity: 0.5;
}}

/* Scrollbars */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {BG_DEEP}; }}
::-webkit-scrollbar-thumb {{ background: rgba(148, 163, 184, 0.15); border-radius: 5px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba(148, 163, 184, 0.3); }}

/* Hide Streamlit branding for a cleaner look */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
</style>
"""


def inject_theme() -> None:
    """Inject premium theme CSS — call once per page, after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, eyebrow: str = "InvestDash", live: bool = True) -> None:
    """Render a premium page header with brand eyebrow and live status badge."""
    timestamp = datetime.now().strftime("%b %d, %Y · %H:%M")
    live_badge = '<span class="status-dot">Live</span>' if live else ""
    html = f"""
    <div class="app-header">
      <div class="app-header-title">
        <span class="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
      </div>
      <div class="app-header-meta">
        {live_badge}
        <span>{timestamp}</span>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def section(label: str) -> None:
    """Render a subtle uppercase section label — replaces st.divider + st.subheader."""
    st.markdown(f'<div class="section-title">{label}</div>', unsafe_allow_html=True)


# ── Plotly chart helpers ───────────────────────────────────────────────

_CHART_FONT = dict(family="Inter, sans-serif", color=TEXT_PRIMARY, size=12)


def apply_chart_theme(
    fig: go.Figure,
    *,
    height: int = 380,
    title: str | None = None,
    show_legend: bool = True,
) -> go.Figure:
    """Apply premium fintech styling to a plotly figure. Idempotent — safe to re-call."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=TEXT_PRIMARY)) if title else None,
        height=height,
        margin=dict(t=40 if title else 20, b=30, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=_CHART_FONT,
        colorway=list(CHART_PALETTE),
        showlegend=show_legend,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDER_SOFT,
            borderwidth=0,
            font=dict(color=TEXT_MUTED, size=11),
        ),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.06)",
            linecolor=BORDER_SOFT,
            zerolinecolor=BORDER_SOFT,
            tickfont=dict(color=TEXT_MUTED, size=11),
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.06)",
            linecolor=BORDER_SOFT,
            zerolinecolor=BORDER_SOFT,
            tickfont=dict(color=TEXT_MUTED, size=11),
        ),
        hoverlabel=dict(
            bgcolor=BG_ELEVATED,
            bordercolor=BORDER_ACCENT,
            font=dict(family="Inter", color=TEXT_PRIMARY, size=12),
        ),
    )
    return fig


def candlestick_colors() -> dict:
    """Colors for go.Candlestick — refined emerald/rose with translucent fills."""
    return dict(
        increasing_line_color=POSITIVE,
        increasing_fillcolor="rgba(16, 185, 129, 0.35)",
        decreasing_line_color=NEGATIVE,
        decreasing_fillcolor="rgba(244, 63, 94, 0.35)",
    )


# ── Formatters ─────────────────────────────────────────────────────────


def fmt_money(v: float, currency: str = "$") -> str:
    return f"{currency}{v:,.2f}"


def fmt_pct(v: float, sign: bool = True) -> str:
    return f"{v:+.2f}%" if sign else f"{v:.2f}%"


def fmt_compact(v: float) -> str:
    """Human-readable compact number (1.2K, 3.4M, 5.6B)."""
    for unit in ("", "K", "M", "B", "T"):
        if abs(v) < 1000:
            return f"{v:,.2f}{unit}" if unit == "" else f"{v:.2f}{unit}"
        v /= 1000
    return f"{v:.2f}Q"


def pl_color(v: float) -> str:
    """CSS color string for P/L values — used in dataframe .map()."""
    if v > 0:
        return f"color: {POSITIVE}; font-weight: 500"
    if v < 0:
        return f"color: {NEGATIVE}; font-weight: 500"
    return f"color: {TEXT_MUTED}"
