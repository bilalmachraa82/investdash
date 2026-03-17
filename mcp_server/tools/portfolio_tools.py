from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.services import ServiceContainer


def register_portfolio_tools(mcp: FastMCP, services: ServiceContainer) -> None:
    @mcp.tool()
    async def portfolio_summary() -> str:
        """Get a complete portfolio summary including total value, gain/loss,
        and allocation breakdowns by sector, asset class, and account."""
        summary = await services.portfolio.get_summary()
        lines = [
            f"Portfolio Summary",
            f"─────────────────────────────────",
            f"Total Value:     ${summary.total_value:,.2f}",
            f"Total Cost:      ${summary.total_cost:,.2f}",
            f"Total Gain/Loss: ${summary.total_gain_loss:,.2f} ({summary.total_gain_loss_pct:+.2f}%)",
            f"Cash:            ${summary.total_cash:,.2f}",
            f"Holdings:        {summary.num_holdings}",
            f"Top Holding:     {summary.top_holding_ticker} ({summary.top_holding_weight_pct:.1f}%)",
            "",
            "Asset Class Allocation:",
        ]
        for ac, pct in sorted(
            summary.asset_class_allocation.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"  {ac:12s} {pct:5.1f}%")

        lines.append("")
        lines.append("Exposure:")
        lines.append(f"  Equity: {summary.equity_pct:.1f}% | Crypto: {summary.crypto_pct:.1f}% | Gold: {summary.gold_pct:.1f}% | Bond: {summary.bond_pct:.1f}% | REIT: {summary.reit_pct:.1f}%")
        return "\n".join(lines)

    @mcp.tool()
    async def portfolio_allocation(allocation_type: str = "asset_class") -> str:
        """Get portfolio allocation breakdown.

        Args:
            allocation_type: One of 'asset_class', 'sector', or 'account'.
        """
        summary = await services.portfolio.get_summary()
        alloc_map = {
            "asset_class": summary.asset_class_allocation,
            "sector": summary.sector_allocation,
            "account": summary.account_allocation,
        }
        alloc = alloc_map.get(allocation_type)
        if alloc is None:
            return f"Unknown allocation type: {allocation_type}. Use 'asset_class', 'sector', or 'account'."

        lines = [f"Allocation by {allocation_type.replace('_', ' ').title()}:", ""]
        for name, pct in sorted(alloc.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(pct / 2)
            lines.append(f"  {name:20s} {pct:5.1f}% {bar}")
        return "\n".join(lines)

    @mcp.tool()
    async def holding_detail(ticker: str) -> str:
        """Get detailed info for a specific holding in the portfolio.

        Args:
            ticker: Stock/ETF/crypto ticker symbol (e.g., 'AAPL', 'BTC-USD').
        """
        h = await services.portfolio.get_holding_detail(ticker)
        if h is None:
            return f"{ticker} not found in portfolio."

        return "\n".join([
            f"{h.name} ({h.ticker})",
            f"─────────────────────────────────",
            f"Asset Class:   {h.asset_class}",
            f"Sector:        {h.sector or 'N/A'}",
            f"Account:       {h.account}",
            f"Quantity:      {h.quantity}",
            f"Cost Basis:    ${h.cost_basis_per_share:,.2f}/share",
            f"Current Price: ${h.current_price:,.2f}",
            f"Current Value: ${h.current_value:,.2f}",
            f"Total Cost:    ${h.total_cost:,.2f}",
            f"Gain/Loss:     ${h.gain_loss:,.2f} ({h.gain_loss_pct:+.2f}%)",
            f"Added:         {h.added_date}",
        ])

    @mcp.tool()
    async def portfolio_holdings() -> str:
        """List all holdings with current values and gain/loss."""
        portfolio = await services.portfolio.get_portfolio()
        lines = [
            f"{'Ticker':<10} {'Name':<25} {'Qty':>8} {'Price':>10} {'Value':>12} {'G/L':>10} {'G/L%':>8}",
            "─" * 85,
        ]
        for h in sorted(portfolio.holdings, key=lambda x: x.current_value, reverse=True):
            lines.append(
                f"{h.ticker:<10} {h.name[:24]:<25} {h.quantity:>8.2f} "
                f"${h.current_price:>9,.2f} ${h.current_value:>11,.2f} "
                f"${h.gain_loss:>9,.2f} {h.gain_loss_pct:>7.1f}%"
            )
        lines.append("─" * 85)
        total_val = sum(h.current_value for h in portfolio.holdings)
        total_cash = sum(portfolio.cash_positions.values())
        lines.append(f"{'Total Holdings':>45} ${total_val:>11,.2f}")
        lines.append(f"{'Cash':>45} ${total_cash:>11,.2f}")
        lines.append(f"{'Grand Total':>45} ${total_val + total_cash:>11,.2f}")
        return "\n".join(lines)
