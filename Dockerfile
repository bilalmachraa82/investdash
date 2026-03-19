FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r investdash && useradd -r -g investdash -d /app investdash

# Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# App source
COPY backend/ backend/
COPY mcp_server/ mcp_server/
COPY pages/ pages/
COPY data/portfolio_manual.json data/portfolio_manual.json
COPY streamlit_app.py .
COPY start.sh .
COPY .streamlit/ .streamlit/

# Data dir for SQLite (created at runtime)
RUN mkdir -p data && chown -R investdash:investdash /app

USER investdash

# Expose ports
EXPOSE 8000 8501

# Run both API + Streamlit in one container
CMD ["bash", "start.sh"]
