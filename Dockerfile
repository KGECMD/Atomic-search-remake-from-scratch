FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Environment
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/data/supernova_index.db

CMD ["gunicorn", "atomic_search.app:app", "--bind", "0.0.0.0:8080"]
