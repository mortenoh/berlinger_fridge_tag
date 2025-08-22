# Multi-stage Dockerfile using Python UV base image
# Stage 1: Build dependencies and install packages
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Copy UV configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual environment
RUN uv sync --frozen --no-dev

# Stage 2: Runtime image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY berlinger_fridge_tag/ ./berlinger_fridge_tag/
COPY api.py cli.py run_api.py ./

# Make sure to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/', timeout=5)"

# Default command to run the API
CMD ["python", "run_api.py"]