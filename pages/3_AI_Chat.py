"""AI Chat — Streaming conversation with Claude about your portfolio."""

import streamlit as st

from backend.client import InvestDashClient

client = InvestDashClient()

# ── Session state ─────────────────────────────────────────────────────

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# ── Page ──────────────────────────────────────────────────────────────

st.title("AI Chat")

# Check API health
try:
    health = client.health()
    if not health.get("ai_available"):
        st.warning("AI chat requires an ANTHROPIC_API_KEY in your .env file.")
        st.stop()
except Exception as e:
    st.error(f"Cannot connect to API: {e}")
    st.stop()

# Suggested prompts
if not st.session_state.chat_messages:
    st.caption("Ask questions about your portfolio, markets, or investment strategies.")
    suggestions = [
        "What's my portfolio summary?",
        "Which of my holdings has the best performance?",
        "Am I too concentrated in tech stocks?",
        "Explain my crypto exposure risk",
    ]
    cols = st.columns(len(suggestions))
    for i, (col, prompt) in enumerate(zip(cols, suggestions)):
        if col.button(prompt, key=f"suggestion_{i}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            st.rerun()

# Display history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Process last user message if no assistant response yet
if (
    st.session_state.chat_messages
    and st.session_state.chat_messages[-1]["role"] == "user"
):
    user_msg = st.session_state.chat_messages[-1]["content"]
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        try:
            for chunk in client.chat_stream(user_msg, st.session_state.conversation_id):
                if "error" in chunk:
                    full_response = f"Error: {chunk['error']}"
                    break
                if "content" in chunk:
                    full_response += chunk["content"]
                    placeholder.markdown(full_response + "▌")
                if "conversation_id" in chunk:
                    st.session_state.conversation_id = chunk["conversation_id"]
                if chunk.get("done"):
                    break
            placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"Connection error: {e}"
            placeholder.error(full_response)

        st.session_state.chat_messages.append({"role": "assistant", "content": full_response})

# Chat input
if prompt := st.chat_input("Ask about your portfolio..."):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    st.rerun()

# Sidebar controls
with st.sidebar:
    if st.button("Clear Chat"):
        st.session_state.chat_messages = []
        st.session_state.conversation_id = None
        st.rerun()
