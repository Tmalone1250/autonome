FROM python:3.11-slim

WORKDIR /app

# We expect the build context to be the BOTCHAIN root directory
# so we can copy both the SDK and the autonome folder.
COPY autonome/requirements.txt /app/autonome/
RUN pip install --no-cache-dir -r /app/autonome/requirements.txt

# Install botchain-sdk-py
COPY botchain-sdk-py/ /app/botchain-sdk-py/
RUN pip install /app/botchain-sdk-py/

# Copy worker application
COPY autonome/ /app/autonome/
# Copy ABIs needed by settlement.py
COPY autonome-contracts/out/ /app/autonome-contracts/out/

ENV PYTHONPATH=/app
ENV OLLAMA_HOST="http://host.docker.internal:11434"

EXPOSE 8000

WORKDIR /app/autonome
CMD ["uvicorn", "worker:app", "--host", "0.0.0.0", "--port", "8000"]
