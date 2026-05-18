# Stage 1: Base configuration shared across environments
FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Stage 2: Development and Testing environment
FROM python:3.11-slim AS test
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-dev.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
RUN playwright install --with-deps
COPY . .
CMD ["python", "-m", "pytest"]

# Stage 3: Clean Production environment for deployment
FROM base AS production
CMD ["python", "app.py"]