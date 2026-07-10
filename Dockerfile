# SuperNova Search Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY main.py .
COPY atomic_search/ ./atomic_search/

# Create dirs
RUN mkdir -p /tmp/atomic_search && chmod 777 /tmp/atomic_search

# Expose default port
EXPOSE 8080

# Run - Railway sets PORT env var
CMD ["sh", "-c", "python -m gunicorn atomic_search.main:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4"]
