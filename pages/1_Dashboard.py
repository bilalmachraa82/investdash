"""Dashboard — KPI cards, allocation charts, market overview."""

import streamlit as st
import plotly.graph_objects as go

from backend.client import InvestDashClient
from backend.ui_theme import (
    apply_chart_theme,
    fmt_money,
    fmt_pct,
    page_header,
    section,
)

client = InvestDashClient()


def render_kpi_cards(summary: dict) -> None:
    cols = st.columns(5)
    cols[0].metric("Total Value", fmt_money(summary["total_value"]))
    cols[1].metric(
        "Gain/Loss",
        fmt_money(summary["total_gain_loss"]),
        fmt_pct(summary["total_gain_loss_pct"]),
    )
    cols[2].metric("Cash", fmt_money(summary["total_cash"]))
    cols[3].metric("Holdings", summary["num_holdings"])
    cols[4].metric(
        "Top Holding",
        summary["top_holding_ticker"],
        f"{summary['top_holding_weight_pct']:.1f}%",
    )


def render_allocation_chart(title: str, data: dict[str, float]) -> None:
    labels = list(data.keys())
    values = list(data.values())
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                textinfo="label+percent",
                textfont=dict(size=11),
                marker=dict(line=dict(color="rgba(0,0,0,0)", width=0)),
            )
        ]
    )
    apply_chart_theme(fig, title=title, height=360, show_legend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_exposure_bars(summary: dict) -> None:
    categories = ["Equity", "Crypto", "Gold", "Bond", "REIT"]
    values = [
        summary["equity_pct"],
        summary["crypto_pct"],
        summary["gold_pct"],
        summary["bond_pct"],
        summary["reit_pct"],
    ]
    fig = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                text=[f"{v:.1f}%" for v in values],
                textposition="outside",
                textfont=dict(size=11),
                marker=dict(
                    line=dict(color="rgba(0,0,0,0)", width=0),
                    cornerradius=6,
                ),
            )
        ]
    )
    fig.update_yaxes(title_text="% of Portfolio")
    apply_chart_theme(fig, title="Asset Class Exposure", height=360, show_legend=False)
    st.plotly_chart(fig, use_container_width=True)


# ── Page ──────────────────────────────────────────────────────────────

page_header("Dashboard", eyebrow="Overview")

try:
    summary = client.get_portfolio_summary()
except Exception as e:
    st.error(f"Failed to connect to API: {e}")
    st.info("Make sure the FastAPI backend is running: `investdash-api`")
    st.stop()

render_kpi_cards(summary)

section("Allocation")
col_left, col_right = st.columns(2)
with col_left:
    render_allocation_chart("Asset Class", summary.get("asset_class_allocation", {}))
with col_right:
    render_allocation_chart("Sector", summary.get("sector_allocation", {}))

section("Exposure")
render_exposure_bars(summary)

section("Market Overview")
try:
    indices = client.get_quotes(["^GSPC", "^DJI", "^IXIC", "^VIX"])
    cols = st.columns(len(indices))
    for col, q in zip(cols, indices):
        col.metric(
            q["ticker"],
            f"{q['price']:,.2f}",
            fmt_pct(q["change_pct"]),
        )
except Exception:
    st.caption("Market index data unavailable.")
