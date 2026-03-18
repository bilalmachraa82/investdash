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
COPY .streamlit/ .streamlit/

# Expose ports: 8000 (API) + 8501 (Streamlit)
EXPOSE 8000 8501

# Default: run FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
