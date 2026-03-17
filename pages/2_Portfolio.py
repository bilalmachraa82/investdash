"""Portfolio — Holdings table, drill-down, allocation breakdown."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from backend.client import InvestDashClient

client = InvestDashClient()


def _color(val: float) -> str:
    if val > 0:
        return "color: #34a853"
    elif val < 0:
        return "color: #ea4335"
    return ""


# ── Page ──────────────────────────────────────────────────────────────

st.title("Portfolio")

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

# Format numbers
money_cols = ["current_price", "cost_basis_per_share", "current_value", "total_cost", "gain_loss"]
for c in money_cols:
    if c in df.columns:
        df[c] = df[c].apply(lambda v: f"${v:,.2f}")

if "gain_loss_pct" in df.columns:
    df["gain_loss_pct"] = df["gain_loss_pct"].apply(lambda v: f"{v:+.2f}%")

st.dataframe(df, use_container_width=True, hide_index=True)

# Cash positions
st.subheader("Cash Positions")
cash_cols = st.columns(len(cash))
for col, (currency, amount) in zip(cash_cols, cash.items()):
    col.metric(currency, f"${amount:,.2f}")

st.divider()

# Drill-down
st.subheader("Holding Detail")
tickers = [h["ticker"] for h in holdings]
selected = st.selectbox("Select a holding", tickers)

if selected:
    try:
        detail = client.get_holding_detail(selected)
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", f"${detail.get('current_price', 0):,.2f}")
        col2.metric("Quantity", f"{detail.get('quantity', 0):,.4f}")
        col3.metric(
            "Gain/Loss",
            f"${detail.get('gain_loss', 0):,.2f}",
            f"{detail.get('gain_loss_pct', 0):+.2f}%",
        )

        # Price chart
        try:
            bars = client.get_history(selected, period="6mo")
            if bars:
                chart_df = pd.DataFrame(bars)
                fig = go.Figure(
                    data=[go.Candlestick(
                        x=chart_df["date"],
                        open=chart_df["open"],
                        high=chart_df["high"],
                        low=chart_df["low"],
                        close=chart_df["close"],
                    )]
                )
                fig.update_layout(
                    title=f"{selected} — 6 Month",
                    height=400,
                    margin=dict(t=40, b=20, l=40, r=20),
                    xaxis_rangeslider_visible=False,
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.caption("Price history unavailable.")
    except Exception as e:
        st.warning(f"Could not load detail for {selected}: {e}")

st.divider()

# Allocation donut
st.subheader("Allocation Breakdown")
alloc_type = st.radio("View by", ["asset_class", "sector", "account"], horizontal=True)

try:
    alloc = client.get_allocation(alloc_type)
    alloc_data = alloc.get("allocation", {})
    if alloc_data:
        labels = list(alloc_data.keys())
        values = list(alloc_data.values())
        fig = go.Figure(
            data=[go.Pie(labels=labels, values=values, hole=0.4)]
        )
        fig.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.caption("Allocation data unavailable.")
