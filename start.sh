#!/bin/bash
# Start both FastAPI and Streamlit in a single container

# Start FastAPI in background
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for API to be ready
echo "Waiting for API to start..."
for i in $(seq 1 30); do
    if python -c "import httpx; httpx.get('http://localhost:8000/api/health')" 2>/dev/null; then
        echo "API is ready!"
        break
    fi
    sleep 1
done

# Start Streamlit (foreground — keeps container alive)
exec streamlit run streamlit_app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
