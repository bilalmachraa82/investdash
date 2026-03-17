"""Research — Symbol search, quote card, price chart, compare mode."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from backend.client import InvestDashClient

client = InvestDashClient()

st.title("Research")

# ── Symbol search ─────────────────────────────────────────────────────

tab_single, tab_compare = st.tabs(["Single Stock", "Compare"])

with tab_single:
    ticker = st.text_input("Enter ticker symbol", value="AAPL", key="research_ticker").upper().strip()

    if ticker:
        try:
            quote = client.get_quote(ticker)
        except Exception as e:
            st.error(f"Could not fetch quote for {ticker}: {e}")
            st.stop()

        # Quote card
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Price", f"${quote['price']:,.2f}", f"{quote['change_pct']:+.2f}%")
        col2.metric("Volume", f"{quote.get('volume', 0):,}")
        col3.metric("Market Cap", f"${quote['market_cap'] / 1e9:,.1f}B" if quote.get("market_cap") else "N/A")
        col4.metric("P/E", f"{quote['pe_ratio']:.1f}" if quote.get("pe_ratio") else "N/A")

        st.divider()

        # Price chart
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
        try:
            bars = client.get_history(ticker, period=period)
            if bars:
                df = pd.DataFrame(bars)
                fig = go.Figure(
                    data=[go.Candlestick(
                        x=df["date"], open=df["open"], high=df["high"],
                        low=df["low"], close=df["close"],
                    )]
                )
                fig.update_layout(
                    title=f"{ticker} — {period}",
                    height=500,
                    xaxis_rangeslider_visible=False,
                    margin=dict(t=40, b=20, l=40, r=20),
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.caption("Price history unavailable.")

        # Fundamentals
        st.subheader("Fundamentals")
        try:
            fund = client.get_fundamentals(ticker)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sector", fund.get("sector") or "N/A")
            c2.metric("Forward P/E", f"{fund['forward_pe']:.1f}" if fund.get("forward_pe") else "N/A")
            c3.metric("Profit Margin", f"{fund['profit_margin'] * 100:.1f}%" if fund.get("profit_margin") else "N/A")
            c4.metric("Dividend Yield", f"{fund['dividend_yield'] * 100:.2f}%" if fund.get("dividend_yield") else "N/A")

            with st.expander("Full Fundamentals"):
                filtered = {k: v for k, v in fund.items() if v is not None and k != "ticker"}
                st.json(filtered)
        except Exception:
            st.caption("Fundamentals unavailable.")


with tab_compare:
    st.caption("Compare up to 4 symbols side by side.")
    compare_input = st.text_input(
        "Tickers (comma-separated)", value="AAPL,MSFT,GOOGL", key="compare_tickers"
    )
    tickers = [t.strip().upper() for t in compare_input.split(",") if t.strip()][:4]

    if tickers and st.button("Compare"):
        try:
            quotes = client.get_quotes(tickers)
        except Exception as e:
            st.error(f"Failed to fetch quotes: {e}")
            st.stop()

        if quotes:
            cols = st.columns(len(quotes))
            for col, q in zip(cols, quotes):
                with col:
                    st.subheader(q["ticker"])
                    st.metric("Price", f"${q['price']:,.2f}", f"{q['change_pct']:+.2f}%")
                    st.caption(f"Vol: {q.get('volume', 0):,}")
                    if q.get("pe_ratio"):
                        st.caption(f"P/E: {q['pe_ratio']:.1f}")

            # Overlay price chart
            st.subheader("Price Comparison (Normalized)")
            compare_period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=2, key="compare_period")
            fig = go.Figure()
            for t in tickers:
                try:
                    bars = client.get_history(t, period=compare_period)
                    if bars:
                        df = pd.DataFrame(bars)
                        base = df["close"].iloc[0]
                        if base > 0:
                            normalized = ((df["close"] / base) - 1) * 100
                            fig.add_trace(go.Scatter(x=df["date"], y=normalized, name=t, mode="lines"))
                except Exception:
                    continue

            fig.update_layout(
                yaxis_title="% Change",
                height=500,
                margin=dict(t=20, b=20, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)
