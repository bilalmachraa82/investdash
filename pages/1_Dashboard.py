"""Dashboard — KPI cards, allocation charts, market overview."""

import streamlit as st
import plotly.graph_objects as go

from backend.client import InvestDashClient

client = InvestDashClient()


def _fmt_money(v: float) -> str:
    return f"${v:,.2f}"


def _fmt_pct(v: float) -> str:
    return f"{v:+.2f}%"


def render_kpi_cards(summary: dict):
    cols = st.columns(5)
    cols[0].metric("Total Value", _fmt_money(summary["total_value"]))
    cols[1].metric(
        "Gain/Loss",
        _fmt_money(summary["total_gain_loss"]),
        _fmt_pct(summary["total_gain_loss_pct"]),
    )
    cols[2].metric("Cash", _fmt_money(summary["total_cash"]))
    cols[3].metric("Holdings", summary["num_holdings"])
    cols[4].metric(
        "Top Holding",
        summary["top_holding_ticker"],
        f"{summary['top_holding_weight_pct']:.1f}%",
    )


def render_allocation_chart(title: str, data: dict[str, float]):
    labels = list(data.keys())
    values = list(data.values())
    fig = go.Figure(
        data=[go.Pie(labels=labels, values=values, hole=0.4, textinfo="label+percent")]
    )
    fig.update_layout(title_text=title, margin=dict(t=40, b=20, l=20, r=20), height=350)
    st.plotly_chart(fig, use_container_width=True)


def render_exposure_bars(summary: dict):
    categories = ["Equity", "Crypto", "Gold", "Bond", "REIT"]
    values = [
        summary["equity_pct"],
        summary["crypto_pct"],
        summary["gold_pct"],
        summary["bond_pct"],
        summary["reit_pct"],
    ]
    colors = ["#4285f4", "#f4b400", "#ffd700", "#34a853", "#ea4335"]
    fig = go.Figure(
        data=[go.Bar(x=categories, y=values, marker_color=colors, text=[f"{v:.1f}%" for v in values], textposition="auto")]
    )
    fig.update_layout(
        title_text="Asset Class Exposure",
        yaxis_title="% of Portfolio",
        margin=dict(t=40, b=20, l=40, r=20),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Page ──────────────────────────────────────────────────────────────

st.title("Dashboard")

try:
    summary = client.get_portfolio_summary()
except Exception as e:
    st.error(f"Failed to connect to API: {e}")
    st.info("Make sure the FastAPI backend is running: `investdash-api`")
    st.stop()

render_kpi_cards(summary)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    render_allocation_chart("Asset Class Allocation", summary.get("asset_class_allocation", {}))

with col_right:
    render_allocation_chart("Sector Allocation", summary.get("sector_allocation", {}))

st.divider()

render_exposure_bars(summary)

# Market overview — index proxies
st.subheader("Market Overview")
try:
    indices = client.get_quotes(["^GSPC", "^DJI", "^IXIC", "^VIX"])
    cols = st.columns(len(indices))
    for col, q in zip(cols, indices):
        col.metric(
            q["ticker"],
            f"{q['price']:,.2f}",
            f"{q['change_pct']:+.2f}%",
        )
except Exception:
    st.caption("Market index data unavailable.")
