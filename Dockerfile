FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY main-packager/ ./main-packager/
COPY transcript-analyzer/ ./transcript-analyzer/
COPY trend-researcher/ ./trend-researcher/
COPY titling-agent/ ./titling-agent/

# Install dependencies
RUN uv pip install --system -e ".[dev]" && \
    uv pip install --system fastapi uvicorn psycopg[binary] langgraph-checkpoint-postgres

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
