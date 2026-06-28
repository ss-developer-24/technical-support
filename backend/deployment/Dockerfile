# Backend Docker container for Google Cloud Run
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
# Build context is backend root, so copy directly
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from build context (backend root)
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /tmp && \
    chown -R appuser:appuser /tmp

USER appuser

# Expose port
EXPOSE 8080

# Run the FastAPI application
# Use shell form to ensure environment variable expansion
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level info
