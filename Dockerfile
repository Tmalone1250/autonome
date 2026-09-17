FROM python:3.11-slim

WORKDIR /app

# ── Step 1: Install botchain-sdk-py (local package, lives one level above autonome) ──
COPY botchain-sdk-py/ ./botchain-sdk-py/
RUN pip install --no-cache-dir ./botchain-sdk-py

# ── Step 2: Install autonome Python dependencies ──
COPY autonome/requirements.txt ./autonome/requirements.txt
RUN pip install --no-cache-dir -r ./autonome/requirements.txt

# ── Step 3: Copy autonome source ──
COPY autonome/ ./autonome/

WORKDIR /app/autonome

ENV PYTHONPATH=/app/autonome
ENV OLLAMA_HOST="http://127.0.0.1:11434"

EXPOSE 8002

CMD ["uvicorn", "orchestrator.engine:app", "--host", "0.0.0.0", "--port", "8002"]
