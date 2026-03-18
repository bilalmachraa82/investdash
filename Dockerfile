FROM python:3.12-slim AS base

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# App source
COPY backend/ backend/
COPY mcp_server/ mcp_server/
COPY pages/ pages/
COPY data/ data/
COPY streamlit_app.py .
COPY start.sh .
COPY .streamlit/ .streamlit/

# Expose ports
EXPOSE 8000 8501

# Run both API + Streamlit in one container
CMD ["bash", "start.sh"]
