# Dockerfile for FamilyFinanceProject
# Using Poetry with proper virtual environment setup

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Set up Poetry environment variables (based on best practices)
ENV PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT="1" \
    POETRY_NO_INTERACTION="1"

# Install Poetry in its own virtual environment
RUN python -m venv "$POETRY_HOME" \
    && "$POETRY_HOME/bin/pip" install poetry \
    && ln -s /opt/poetry/bin/poetry /usr/bin/poetry

# Copy Poetry files first (for better caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies and create virtual environment in project
RUN poetry install --only=main

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Copy Docker utilities and set permissions
COPY docker/entrypoint.sh docker/healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories and set all permissions
RUN mkdir -p voice_messages && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command - now using Python directly from virtual environment via PATH
CMD ["python", "run_server.py"]