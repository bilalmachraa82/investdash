"""Research — Symbol search, quote card, price chart, compare mode."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from backend.client import InvestDashClient
from backend.ui_theme import (
    CHART_PALETTE,
    apply_chart_theme,
    candlestick_colors,
    fmt_money,
    fmt_pct,
    page_header,
    section,
)

client = InvestDashClient()

page_header("Research", eyebrow="Markets")

tab_single, tab_compare = st.tabs(["Single Stock", "Compare"])

with tab_single:
    ticker = st.text_input(
        "Enter ticker symbol", value="AAPL", key="research_ticker"
    ).upper().strip()

    if ticker:
        try:
            quote = client.get_quote(ticker)
        except Exception as e:
            st.error(f"Could not fetch quote for {ticker}: {e}")
            st.stop()

        # Quote card
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Price", fmt_money(quote["price"]), fmt_pct(quote["change_pct"]))
        col2.metric("Volume", f"{quote.get('volume', 0):,}")
        col3.metric(
            "Market Cap",
            f"${quote['market_cap'] / 1e9:,.1f}B" if quote.get("market_cap") else "N/A",
        )
        col4.metric("P/E", f"{quote['pe_ratio']:.1f}" if quote.get("pe_ratio") else "N/A")

        section("Price History")
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
        try:
            bars = client.get_history(ticker, period=period)
            if bars:
                df = pd.DataFrame(bars)
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=df["date"],
                            open=df["open"],
                            high=df["high"],
                            low=df["low"],
                            close=df["close"],
                            **candlestick_colors(),
                        )
                    ]
                )
                fig.update_layout(xaxis_rangeslider_visible=False)
                apply_chart_theme(fig, title=f"{ticker} · {period}", height=500, show_legend=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.caption("Price history unavailable.")

        section("Fundamentals")
        try:
            fund = client.get_fundamentals(ticker)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sector", fund.get("sector") or "N/A")
            c2.metric("Forward P/E", f"{fund['forward_pe']:.1f}" if fund.get("forward_pe") else "N/A")
            c3.metric(
                "Profit Margin",
                f"{fund['profit_margin'] * 100:.1f}%" if fund.get("profit_margin") else "N/A",
            )
            c4.metric(
                "Dividend Yield",
                f"{fund['dividend_yield'] * 100:.2f}%" if fund.get("dividend_yield") else "N/A",
            )

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
                    st.metric("Price", fmt_money(q["price"]), fmt_pct(q["change_pct"]))
                    st.caption(f"Vol: {q.get('volume', 0):,}")
                    if q.get("pe_ratio"):
                        st.caption(f"P/E: {q['pe_ratio']:.1f}")

            section("Price Comparison (Normalized)")
            compare_period = st.selectbox(
                "Period", ["1mo", "3mo", "6mo", "1y"], index=2, key="compare_period"
            )
            fig = go.Figure()
            for idx, t in enumerate(tickers):
                try:
                    bars = client.get_history(t, period=compare_period)
                    if bars:
                        df = pd.DataFrame(bars)
                        base = df["close"].iloc[0]
                        if base > 0:
                            normalized = ((df["close"] / base) - 1) * 100
                            fig.add_trace(
                                go.Scatter(
                                    x=df["date"],
                                    y=normalized,
                                    name=t,
                                    mode="lines",
                                    line=dict(
                                        color=CHART_PALETTE[idx % len(CHART_PALETTE)],
                                        width=2,
                                    ),
                                )
                            )
                except Exception:
                    continue

            fig.update_yaxes(title_text="% Change")
            fig.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            )
            apply_chart_theme(fig, height=500, show_legend=True)
            st.plotly_chart(fig, use_container_width=True)
