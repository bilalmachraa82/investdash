from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.services import ServiceContainer


def register_analysis_tools(mcp: FastMCP, services: ServiceContainer) -> None:
    @mcp.tool()
    async def risk_metrics() -> str:
        """Analyze portfolio risk: concentration, diversification, exposure levels."""
        summary = await services.portfolio.get_summary()
        portfolio = await services.portfolio.get_portfolio()

        warnings = []

        # Concentration risk
        if summary.top_holding_weight_pct > 25:
            warnings.append(
                f"HIGH CONCENTRATION: {summary.top_holding_ticker} is "
                f"{summary.top_holding_weight_pct:.1f}% of portfolio"
            )

        # Asset class checks
        if summary.crypto_pct > 20:
            warnings.append(f"HIGH CRYPTO EXPOSURE: {summary.crypto_pct:.1f}%")
        if summary.equity_pct > 80:
            warnings.append(f"HIGH EQUITY EXPOSURE: {summary.equity_pct:.1f}%")
        if summary.bond_pct < 5 and summary.total_value > 50000:
            warnings.append(f"LOW BOND ALLOCATION: {summary.bond_pct:.1f}%")

        # Sector concentration
        max_sector = max(
            summary.sector_allocation.items(), key=lambda x: x[1], default=("", 0)
        )
        if max_sector[1] > 40:
            warnings.append(
                f"SECTOR CONCENTRATION: {max_sector[0]} at {max_sector[1]:.1f}%"
            )

        # Cash drag
        cash_pct = (
            summary.total_cash / summary.total_value * 100
            if summary.total_value
            else 0
        )
        if cash_pct > 20:
            warnings.append(f"HIGH CASH: {cash_pct:.1f}% uninvested")

        lines = [
            "Portfolio Risk Analysis",
            "─────────────────────────────────",
            f"Holdings:            {summary.num_holdings}",
            f"Top Holding:         {summary.top_holding_ticker} ({summary.top_holding_weight_pct:.1f}%)",
            f"Equity Exposure:     {summary.equity_pct:.1f}%",
            f"Crypto Exposure:     {summary.crypto_pct:.1f}%",
            f"Gold Exposure:       {summary.gold_pct:.1f}%",
            f"Bond Exposure:       {summary.bond_pct:.1f}%",
            f"REIT Exposure:       {summary.reit_pct:.1f}%",
            f"Cash:                {cash_pct:.1f}%",
            f"Unique Sectors:      {len(summary.sector_allocation)}",
            "",
        ]

        if warnings:
            lines.append("⚠ Warnings:")
            for w in warnings:
                lines.append(f"  • {w}")
        else:
            lines.append("✓ No major risk flags detected")

        return "\n".join(lines)

    @mcp.tool()
    async def rate_exposure() -> str:
        """Analyze portfolio exposure to interest rate changes."""
        summary = await services.portfolio.get_summary()
        macro = await services.market_data.get_macro_snapshot()

        lines = [
            "Interest Rate Exposure",
            "─────────────────────────────────",
        ]

        if macro.treasury_10y:
            lines.append(f"10Y Treasury: {macro.treasury_10y:.3f}%")
        if macro.yield_curve_spread is not None:
            status = "INVERTED" if macro.yield_curve_inverted else "Normal"
            lines.append(f"Yield Curve:  {macro.yield_curve_spread:+.3f}% ({status})")

        lines.append("")
        lines.append("Rate-Sensitive Holdings:")
        lines.append(f"  Bonds:  {summary.bond_pct:.1f}% (directly impacted)")
        lines.append(f"  REITs:  {summary.reit_pct:.1f}% (inversely correlated)")
        lines.append(f"  Gold:   {summary.gold_pct:.1f}% (rate hedge)")

        total_sensitive = summary.bond_pct + summary.reit_pct
        lines.append(f"\nTotal Rate-Sensitive: {total_sensitive:.1f}%")

        if macro.yield_curve_inverted:
            lines.append("\n⚠ Yield curve inverted — historically signals recession risk")

        return "\n".join(lines)

    @mcp.tool()
    async def hedge_analysis() -> str:
        """Analyze defensive/hedge positions in the portfolio."""
        summary = await services.portfolio.get_summary()

        hedge_pct = summary.gold_pct + summary.bond_pct
        cash_pct = (
            summary.total_cash / summary.total_value * 100
            if summary.total_value
            else 0
        )
        total_defensive = hedge_pct + cash_pct

        lines = [
            "Hedge & Defensive Analysis",
            "─────────────────────────────────",
            f"Gold/Commodities: {summary.gold_pct:.1f}%",
            f"Bonds:            {summary.bond_pct:.1f}%",
            f"Cash:             {cash_pct:.1f}%",
            f"Total Defensive:  {total_defensive:.1f}%",
            "",
            f"Growth/Risk Assets:",
            f"  Equity: {summary.equity_pct:.1f}%",
            f"  Crypto: {summary.crypto_pct:.1f}%",
            f"  REIT:   {summary.reit_pct:.1f}%",
            "",
        ]

        if total_defensive < 15:
            lines.append("⚠ LOW HEDGE: Consider adding bonds or gold for downside protection")
        elif total_defensive > 50:
            lines.append("Note: Very defensive positioning — may underperform in bull market")
        else:
            lines.append("✓ Reasonable hedge allocation")

        return "\n".join(lines)

    @mcp.tool()
    async def performance_overview() -> str:
        """Get portfolio performance: gain/loss by holding, sorted by P&L."""
        portfolio = await services.portfolio.get_portfolio()
        holdings = sorted(
            portfolio.holdings, key=lambda h: h.gain_loss, reverse=True
        )

        total_gl = sum(h.gain_loss for h in holdings)
        winners = [h for h in holdings if h.gain_loss > 0]
        losers = [h for h in holdings if h.gain_loss < 0]

        lines = [
            "Performance Overview",
            "─────────────────────────────────",
            f"{'Ticker':<10} {'Cost':>10} {'Value':>10} {'G/L':>10} {'G/L%':>8}",
            "─" * 50,
        ]
        for h in holdings:
            lines.append(
                f"{h.ticker:<10} ${h.total_cost:>9,.0f} ${h.current_value:>9,.0f} "
                f"${h.gain_loss:>9,.0f} {h.gain_loss_pct:>7.1f}%"
            )
        lines.append("─" * 50)
        lines.append(f"{'Total':>32} ${total_gl:>9,.0f}")
        lines.append(f"\nWinners: {len(winners)} | Losers: {len(losers)}")

        return "\n".join(lines)

    @mcp.tool()
    async def dividend_calendar() -> str:
        """Show dividend-paying holdings with yield information."""
        portfolio = await services.portfolio.get_portfolio()
        tickers = [h.ticker for h in portfolio.holdings]
        quotes = await services.market_data.get_quotes(tickers)

        div_holdings = []
        for h in portfolio.holdings:
            q = next((q for q in quotes if q.ticker == h.ticker.upper()), None)
            if q and q.dividend_yield and q.dividend_yield > 0:
                annual_income = h.current_value * q.dividend_yield
                div_holdings.append((h, q.dividend_yield, annual_income))

        if not div_holdings:
            return "No dividend-paying holdings found."

        div_holdings.sort(key=lambda x: x[2], reverse=True)
        total_income = sum(x[2] for x in div_holdings)

        lines = [
            "Dividend Calendar",
            "─────────────────────────────────",
            f"{'Ticker':<10} {'Yield':>8} {'Value':>12} {'Est Income':>12}",
            "─" * 44,
        ]
        for h, yld, income in div_holdings:
            lines.append(
                f"{h.ticker:<10} {yld * 100:>7.2f}% ${h.current_value:>11,.0f} ${income:>11,.0f}"
            )
        lines.append("─" * 44)
        lines.append(f"Total Estimated Annual Income: ${total_income:,.0f}")

        return "\n".join(lines)
