from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.services import ServiceContainer


def register_market_tools(mcp: FastMCP, services: ServiceContainer) -> None:
    @mcp.tool()
    async def stock_quote(ticker: str) -> str:
        """Get a real-time stock/ETF/crypto quote.

        Args:
            ticker: Symbol (e.g., 'AAPL', 'VOO', 'BTC-USD', 'GLD').
        """
        q = await services.market_data.get_quote(ticker)
        sign = "+" if q.change >= 0 else ""
        lines = [
            f"{q.ticker}  ${q.price:,.4f}  {sign}{q.change:,.4f} ({sign}{q.change_pct:.2f}%)",
            f"Volume: {q.volume:,}" if q.volume else "",
            f"52w Range: ${q.fifty_two_week_low:,.2f} - ${q.fifty_two_week_high:,.2f}" if q.fifty_two_week_high else "",
            f"Sector: {q.sector}" if q.sector else "",
        ]
        if q.pe_ratio:
            lines.append(f"P/E: {q.pe_ratio:.2f}")
        if q.market_cap:
            lines.append(f"Market Cap: ${q.market_cap / 1e9:.1f}B")
        return "\n".join(l for l in lines if l)

    @mcp.tool()
    async def stock_history(
        ticker: str, period: str = "1y", interval: str = "1d"
    ) -> str:
        """Get historical price data for a ticker.

        Args:
            ticker: Symbol (e.g., 'AAPL', 'BTC-USD').
            period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max').
            interval: Data interval ('1d', '1wk', '1mo').
        """
        bars = await services.market_data.get_history(ticker, period, interval)
        if not bars:
            return f"No history found for {ticker}"

        lines = [
            f"{ticker.upper()} — {period} ({interval})",
            f"{'Date':<12} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} {'Volume':>12}",
            "─" * 68,
        ]
        # Show last 20 bars max
        for b in bars[-20:]:
            lines.append(
                f"{b.date:<12} {b.open:>10.2f} {b.high:>10.2f} "
                f"{b.low:>10.2f} {b.close:>10.2f} {b.volume:>12,}"
            )
        if len(bars) > 20:
            lines.insert(3, f"... showing last 20 of {len(bars)} bars ...")
        return "\n".join(lines)

    @mcp.tool()
    async def stock_fundamentals(ticker: str) -> str:
        """Get fundamental analysis data for a stock.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT').
        """
        f = await services.market_data.get_fundamentals(ticker)
        lines = [
            f"{f.name} ({f.ticker})",
            f"─────────────────────────────────",
            f"Sector:     {f.sector or 'N/A'}",
            f"Industry:   {f.industry or 'N/A'}",
        ]
        if f.market_cap:
            lines.append(f"Market Cap: ${f.market_cap / 1e9:.1f}B")

        lines.append("")
        lines.append("Valuation:")
        for label, val in [
            ("P/E", f.pe_ratio), ("Fwd P/E", f.forward_pe), ("PEG", f.peg_ratio),
            ("P/B", f.price_to_book), ("P/S", f.price_to_sales), ("EV/EBITDA", f.ev_to_ebitda),
        ]:
            if val is not None:
                lines.append(f"  {label:<10} {val:.2f}")

        lines.append("")
        lines.append("Profitability:")
        for label, val in [
            ("Margin", f.profit_margin), ("Op Margin", f.operating_margin),
            ("ROE", f.roe), ("ROA", f.roa),
        ]:
            if val is not None:
                lines.append(f"  {label:<10} {val * 100:.1f}%")

        if f.analyst_recommendation:
            lines.append("")
            lines.append(f"Analyst: {f.analyst_recommendation}")
            if f.analyst_target_mean:
                lines.append(f"Target:  ${f.analyst_target_mean:.2f}")

        return "\n".join(lines)

    @mcp.tool()
    async def macro_snapshot() -> str:
        """Get current macroeconomic indicators (treasury yields, gold, etc.)."""
        m = await services.market_data.get_macro_snapshot()
        lines = ["Macro Snapshot", "─────────────────────────────────"]
        if m.treasury_2y is not None:
            lines.append(f"2Y Treasury:  {m.treasury_2y:.3f}%")
        if m.treasury_10y is not None:
            lines.append(f"10Y Treasury: {m.treasury_10y:.3f}%")
        if m.treasury_30y is not None:
            lines.append(f"30Y Treasury: {m.treasury_30y:.3f}%")
        if m.yield_curve_spread is not None:
            status = "INVERTED" if m.yield_curve_inverted else "normal"
            lines.append(f"Yield Curve:  {m.yield_curve_spread:+.3f}% ({status})")
        if m.gold_spot_usd is not None:
            lines.append(f"Gold Spot:    ${m.gold_spot_usd:,.2f}")
        return "\n".join(lines)

    @mcp.tool()
    async def compare_stocks(tickers: str) -> str:
        """Compare multiple stocks side by side.

        Args:
            tickers: Comma-separated ticker symbols (e.g., 'AAPL,MSFT,GOOGL').
        """
        ticker_list = [t.strip() for t in tickers.split(",")]
        quotes = await services.market_data.get_quotes(ticker_list)
        if not quotes:
            return "No quotes found."

        lines = [
            f"{'Ticker':<8} {'Price':>10} {'Change':>10} {'Chg%':>8} {'Volume':>14} {'P/E':>8} {'Mkt Cap':>10}",
            "─" * 72,
        ]
        for q in quotes:
            sign = "+" if q.change >= 0 else ""
            mc = f"${q.market_cap / 1e9:.0f}B" if q.market_cap else "N/A"
            pe = f"{q.pe_ratio:.1f}" if q.pe_ratio else "N/A"
            lines.append(
                f"{q.ticker:<8} ${q.price:>9,.2f} {sign}{q.change:>9,.2f} "
                f"{sign}{q.change_pct:>6.1f}% {q.volume:>13,} {pe:>8} {mc:>10}"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def crypto_quote(symbol: str = "BTC-USD") -> str:
        """Get cryptocurrency quote (uses yfinance format like 'BTC-USD', 'ETH-USD').

        Args:
            symbol: Crypto symbol in yfinance format (e.g., 'BTC-USD', 'ETH-USD', 'SOL-USD').
        """
        if not symbol.endswith("-USD"):
            symbol = f"{symbol}-USD"
        q = await services.market_data.get_quote(symbol)
        sign = "+" if q.change >= 0 else ""
        return (
            f"{q.ticker}  ${q.price:,.2f}  {sign}{q.change:,.2f} ({sign}{q.change_pct:.2f}%)\n"
            f"24h Volume: {q.volume:,}"
        )
