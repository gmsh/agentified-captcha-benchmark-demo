# Stage 1: Builder stage
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS builder

# Set working directory
WORKDIR /app

# Copy dependency files and README (needed for package build)
COPY pyproject.toml uv.lock README.md ./

# Copy source code (needed for package build)
COPY src/ ./src/

# Install dependencies into /app/.venv
RUN uv sync --frozen --no-dev

# Stage 2: Runtime stage
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY scenarios/opencaptchaworld/ ./scenarios/opencaptchaworld/
COPY assets/opencaptchaworld/ ./assets/opencaptchaworld/

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Environment variables for production
ENV PYTHONUNBUFFERED=1

# Expose ports (documentation only)
EXPOSE 9010 9020

# Entry point: Run the green agent by default
CMD ["python", "scenarios/opencaptchaworld/opencaptchaworld_judge.py", "--host", "0.0.0.0", "--port", "9010"]
