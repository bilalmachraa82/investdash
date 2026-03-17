"""Trading — Alpaca paper trading with order form, positions, and history."""

import streamlit as st
import pandas as pd

from backend.client import InvestDashClient

client = InvestDashClient()

st.title("Trading")

# ── Check trading availability ──────────────────────────────────────
try:
    status = client.get_trading_status()
except Exception as e:
    st.error(f"Cannot connect to API: {e}")
    st.stop()

if status.get("status") == "not_configured":
    st.info("Paper trading requires Alpaca API keys.")
    st.markdown(
        """
        ### Setup Instructions

        1. Create a free paper trading account at [Alpaca](https://alpaca.markets)
        2. Get your API key and secret from the dashboard
        3. Add to your `.env` file:
        ```
        ALPACA_API_KEY=your_key
        ALPACA_SECRET_KEY=your_secret
        ```
        4. Restart the API server

        Trading features include:
        - **Paper trading** — Practice with virtual money
        - **Safety limits** — 10% max per trade, $10k max, 20 trades/day
        - **2-step flow** — Preview before you execute
        - **AI suggestions** — Claude can suggest trades for you to review
        """
    )
    st.stop()

# ── Trading is active — build the UI ────────────────────────────────
st.caption("Paper Trading via Alpaca")

# Tabs
tab_order, tab_positions, tab_orders, tab_history, tab_account = st.tabs(
    ["New Order", "Positions", "Open Orders", "Trade History", "Account"]
)

# ===================================================================
# TAB 1: New Order (preview → confirm → execute)
# ===================================================================
with tab_order:
    st.subheader("Place an Order")

    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", value="AAPL", max_chars=10).strip().upper()
        side = st.selectbox("Side", ["buy", "sell"])
        quantity = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0)

    with col2:
        order_type = st.selectbox("Order Type", ["market", "limit", "stop", "stop_limit"])
        limit_price = None
        stop_price = None
        if order_type in ("limit", "stop_limit"):
            limit_price = st.number_input("Limit Price ($)", min_value=0.01, step=0.01, format="%.2f")
        if order_type in ("stop", "stop_limit"):
            stop_price = st.number_input("Stop Price ($)", min_value=0.01, step=0.01, format="%.2f")
        time_in_force = st.selectbox("Time in Force", ["day", "gtc", "ioc"])

    # Build trade payload
    trade_payload = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "time_in_force": time_in_force,
        "paper": True,
        "broker": "alpaca",
    }
    if limit_price is not None:
        trade_payload["limit_price"] = limit_price
    if stop_price is not None:
        trade_payload["stop_price"] = stop_price

    # Session state for preview flow
    if "trade_preview" not in st.session_state:
        st.session_state.trade_preview = None

    # Preview button
    if st.button("Preview Order", type="primary", use_container_width=True):
        if not symbol:
            st.warning("Enter a symbol.")
        else:
            with st.spinner("Running safety checks..."):
                try:
                    preview = client.preview_trade(trade_payload)
                    st.session_state.trade_preview = preview
                except Exception as e:
                    error_detail = str(e)
                    # Extract detail from HTTP errors
                    if hasattr(e, "response") and e.response is not None:
                        try:
                            error_detail = e.response.json().get("detail", error_detail)
                        except Exception:
                            pass
                    st.error(f"Preview failed: {error_detail}")
                    st.session_state.trade_preview = None

    # Show preview card
    preview = st.session_state.trade_preview
    if preview is not None:
        st.divider()
        st.subheader("Order Preview")

        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Symbol", preview["symbol"])
        pc2.metric("Side", preview["side"].upper())
        pc3.metric("Quantity", f"{preview['quantity']:g}")

        pc4, pc5, pc6 = st.columns(3)
        pc4.metric("Current Price", f"${preview['current_price']:,.2f}")
        pc5.metric("Estimated Total", f"${preview['estimated_total']:,.2f}")
        pc6.metric("Portfolio Impact", f"{preview['portfolio_impact_pct']:.2f}%")

        st.caption(f"Order type: {preview['order_type']}  |  Account: {preview['account_mode']}  |  Broker: {preview['broker']}")

        # Warnings
        for w in preview.get("warnings", []):
            st.warning(w)

        # Confirm & Execute
        col_exec, col_cancel = st.columns(2)
        with col_exec:
            if st.button("Confirm & Execute", type="primary", use_container_width=True):
                with st.spinner("Submitting order..."):
                    try:
                        result = client.execute_trade(trade_payload)
                        st.session_state.trade_preview = None
                        st.success(
                            f"Order {result['status']}! "
                            f"ID: `{result['order_id']}` — {result['message']}"
                        )
                        if result.get("filled_price"):
                            st.info(f"Filled at ${result['filled_price']:,.2f}")
                    except Exception as e:
                        error_detail = str(e)
                        if hasattr(e, "response") and e.response is not None:
                            try:
                                error_detail = e.response.json().get("detail", error_detail)
                            except Exception:
                                pass
                        st.error(f"Execution failed: {error_detail}")
        with col_cancel:
            if st.button("Cancel", use_container_width=True):
                st.session_state.trade_preview = None
                st.rerun()

# ===================================================================
# TAB 2: Positions
# ===================================================================
with tab_positions:
    st.subheader("Current Positions")
    try:
        positions = client.get_positions()
        if not positions:
            st.info("No open positions.")
        else:
            df = pd.DataFrame(positions)
            # Convert numeric columns
            for col in ["qty", "market_value", "cost_basis", "unrealized_pl", "unrealized_plpc", "current_price", "avg_entry_price"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Format display
            display_df = df[["symbol", "qty", "current_price", "avg_entry_price", "market_value", "unrealized_pl", "unrealized_plpc"]].copy()
            display_df.columns = ["Symbol", "Qty", "Price", "Avg Entry", "Market Value", "P/L ($)", "P/L (%)"]

            # Color P/L
            def color_pl(val):
                if val > 0:
                    return "color: #10b981"
                elif val < 0:
                    return "color: #ef4444"
                return ""

            st.dataframe(
                display_df.style
                    .format({"Price": "${:,.2f}", "Avg Entry": "${:,.2f}", "Market Value": "${:,.2f}", "P/L ($)": "${:,.2f}", "P/L (%)": "{:.2%}"})
                    .map(color_pl, subset=["P/L ($)", "P/L (%)"]),
                use_container_width=True,
                hide_index=True,
            )

            total_value = df["market_value"].sum()
            total_pl = df["unrealized_pl"].sum()
            mc1, mc2 = st.columns(2)
            mc1.metric("Total Market Value", f"${total_value:,.2f}")
            mc2.metric("Total Unrealized P/L", f"${total_pl:,.2f}", delta=f"${total_pl:,.2f}")
    except Exception as e:
        st.error(f"Could not load positions: {e}")

# ===================================================================
# TAB 3: Open Orders
# ===================================================================
with tab_orders:
    st.subheader("Open Orders")
    try:
        orders = client.get_orders()
        if not orders:
            st.info("No open orders.")
        else:
            for order in orders:
                with st.container(border=True):
                    oc1, oc2, oc3, oc4 = st.columns([2, 1, 1, 1])
                    oc1.write(f"**{order['symbol']}** — {order['side'].upper()}")
                    oc2.write(f"Qty: {order['qty']}")
                    oc3.write(f"Type: {order['type']}")
                    oc4.write(f"Status: {order['status']}")

                    if order.get("limit_price"):
                        st.caption(f"Limit: ${float(order['limit_price']):,.2f}")
                    if order.get("stop_price"):
                        st.caption(f"Stop: ${float(order['stop_price']):,.2f}")

                    st.caption(f"Created: {order['created_at']}")

                    if st.button(f"Cancel", key=f"cancel_{order['id']}"):
                        try:
                            client.cancel_order(order["id"])
                            st.success(f"Order {order['id'][:8]}... cancelled.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Cancel failed: {e}")
    except Exception as e:
        st.error(f"Could not load orders: {e}")

# ===================================================================
# TAB 4: Trade History
# ===================================================================
with tab_history:
    st.subheader("Trade History")
    try:
        log = client.get_trade_log(limit=100)
        if not log:
            st.info("No trades yet. Place your first order!")
        else:
            df = pd.DataFrame(log)
            display_cols = ["timestamp", "symbol", "side", "quantity", "order_type", "status", "filled_price", "filled_quantity"]
            available_cols = [c for c in display_cols if c in df.columns]
            display_df = df[available_cols].copy()

            col_rename = {
                "timestamp": "Time",
                "symbol": "Symbol",
                "side": "Side",
                "quantity": "Qty",
                "order_type": "Type",
                "status": "Status",
                "filled_price": "Fill Price",
                "filled_quantity": "Fill Qty",
            }
            display_df.rename(columns=col_rename, inplace=True)

            st.dataframe(display_df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Could not load trade history: {e}")

# ===================================================================
# TAB 5: Account Overview
# ===================================================================
with tab_account:
    st.subheader("Alpaca Paper Account")
    try:
        acct = client.get_account()

        a1, a2, a3 = st.columns(3)
        a1.metric("Portfolio Value", f"${float(acct['portfolio_value']):,.2f}")
        a2.metric("Cash", f"${float(acct['cash']):,.2f}")
        a3.metric("Buying Power", f"${float(acct['buying_power']):,.2f}")

        a4, a5, a6 = st.columns(3)
        a4.metric("Equity", f"${float(acct['equity']):,.2f}")
        a5.metric("Status", acct["status"].upper())
        a6.metric("Currency", acct.get("currency", "USD"))

        st.divider()
        st.caption("Safety Limits")
        sl1, sl2, sl3 = st.columns(3)
        sl1.write("Max single order: **10% of portfolio**")
        sl2.write("Max single order: **$10,000**")
        sl3.write("Daily trade limit: **20 trades**")

        if acct.get("pattern_day_trader"):
            st.warning("Account flagged as pattern day trader.")
        if acct.get("trading_blocked"):
            st.error("Trading is currently blocked on this account.")
        if acct.get("account_blocked"):
            st.error("This account is blocked.")
    except Exception as e:
        st.error(f"Could not load account info: {e}")
