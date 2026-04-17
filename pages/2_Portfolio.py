"""Portfolio — Holdings table, drill-down, allocation breakdown."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from backend.client import InvestDashClient
from backend.ui_theme import (
    apply_chart_theme,
    candlestick_colors,
    fmt_money,
    fmt_pct,
    page_header,
    pl_color,
    section,
)

client = InvestDashClient()

# ── Page ──────────────────────────────────────────────────────────────

page_header("Portfolio", eyebrow="Holdings")

try:
    data = client.get_holdings()
except Exception as e:
    st.error(f"Failed to connect to API: {e}")
    st.stop()

holdings = data["holdings"]
cash = data["cash_positions"]

if not holdings:
    st.info("No holdings found. Add positions in data/portfolio_manual.json.")
    st.stop()

# Build dataframe
df = pd.DataFrame(holdings)
display_cols = [
    "ticker", "name", "quantity", "current_price",
    "cost_basis_per_share", "current_value", "total_cost",
    "gain_loss", "gain_loss_pct", "asset_class", "sector", "account",
]
df = df[[c for c in display_cols if c in df.columns]]

# Keep numeric gain_loss for coloring; format others as strings
numeric_gain_loss = df["gain_loss"].copy() if "gain_loss" in df.columns else None
numeric_gain_loss_pct = df["gain_loss_pct"].copy() if "gain_loss_pct" in df.columns else None

styled = df.style.format(
    {
        "current_price": "${:,.2f}",
        "cost_basis_per_share": "${:,.2f}",
        "current_value": "${:,.2f}",
        "total_cost": "${:,.2f}",
        "gain_loss": "${:+,.2f}",
        "gain_loss_pct": "{:+.2f}%",
        "quantity": "{:,.4f}",
    },
    na_rep="—",
)

if numeric_gain_loss is not None:
    styled = styled.map(pl_color, subset=["gain_loss"])
if numeric_gain_loss_pct is not None:
    styled = styled.map(pl_color, subset=["gain_loss_pct"])

st.dataframe(styled, use_container_width=True, hide_index=True)

# Cash positions
section("Cash Positions")
cash_cols = st.columns(len(cash))
for col, (currency, amount) in zip(cash_cols, cash.items()):
    col.metric(currency, fmt_money(amount))

# Drill-down
section("Holding Detail")
tickers = [h["ticker"] for h in holdings]
selected = st.selectbox("Select a holding", tickers, label_visibility="collapsed")

if selected:
    try:
        detail = client.get_holding_detail(selected)
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", fmt_money(detail.get("current_price", 0)))
        col2.metric("Quantity", f"{detail.get('quantity', 0):,.4f}")
        col3.metric(
            "Gain/Loss",
            fmt_money(detail.get("gain_loss", 0)),
            fmt_pct(detail.get("gain_loss_pct", 0)),
        )

        try:
            bars = client.get_history(selected, period="6mo")
            if bars:
                chart_df = pd.DataFrame(bars)
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=chart_df["date"],
                            open=chart_df["open"],
                            high=chart_df["high"],
                            low=chart_df["low"],
                            close=chart_df["close"],
                            **candlestick_colors(),
                        )
                    ]
                )
                fig.update_layout(xaxis_rangeslider_visible=False)
                apply_chart_theme(fig, title=f"{selected} · 6 Month", height=420, show_legend=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.caption("Price history unavailable.")
    except Exception as e:
        st.warning(f"Could not load detail for {selected}: {e}")

# Allocation donut
section("Allocation Breakdown")
alloc_type = st.radio(
    "View by", ["asset_class", "sector", "account"], horizontal=True, label_visibility="collapsed"
)

try:
    alloc = client.get_allocation(alloc_type)
    alloc_data = alloc.get("allocation", {})
    if alloc_data:
        labels = list(alloc_data.keys())
        values = list(alloc_data.values())
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.55,
                    marker=dict(line=dict(color="rgba(0,0,0,0)", width=0)),
                )
            ]
        )
        apply_chart_theme(fig, height=420, show_legend=True)
        st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.caption("Allocation data unavailable.")
