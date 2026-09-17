FROM python:3.11-slim

WORKDIR /app/autonome

# ── Step 1: Install botchain-sdk-py directly from GitHub main branch archive ──
RUN pip install --no-cache-dir https://github.com/Tmalone1250/botchain-sdk-py/archive/refs/heads/main.zip

# ── Step 2: Install autonome Python dependencies ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Step 3: Copy entire autonome workspace ──
COPY . .

ENV PYTHONPATH=/app/autonome
ENV OLLAMA_HOST="http://127.0.0.1:11434"

EXPOSE 8002

CMD ["uvicorn", "orchestrator.engine:app", "--host", "0.0.0.0", "--port", "8002"]
