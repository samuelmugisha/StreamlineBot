FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Single worker — required for the in-memory ingest lock to work correctly.
# If you need multiple workers, replace the threading lock in main.py with
# a distributed lock (Redis or database row) first.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
