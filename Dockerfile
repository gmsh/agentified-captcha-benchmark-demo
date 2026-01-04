# Stage 1: Builder stage
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

# Set working directory
WORKDIR /app

# Copy dependency files and README (needed for package build)
COPY pyproject.toml uv.lock README.md ./

# Copy source code (needed for package build)
COPY src/ ./src/

# Install dependencies into /app/.venv with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Stage 2: Runtime stage
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

# Create non-root user
RUN adduser --disabled-password --gecos '' agent

# Set working directory
WORKDIR /home/agent

# Copy project files needed for uv run
COPY --chown=agent:agent pyproject.toml uv.lock README.md ./

# Copy virtual environment from builder
COPY --from=builder --chown=agent:agent /app/.venv /home/agent/.venv

# Copy application code
COPY --chown=agent:agent src/ ./src/
COPY --chown=agent:agent scenarios/opencaptchaworld/ ./scenarios/opencaptchaworld/
COPY --chown=agent:agent assets/opencaptchaworld/ ./assets/opencaptchaworld/

# Environment variables for production
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER agent

# Expose ports (documentation only)
EXPOSE 9010 9020

# Entry point: Run the green agent by default
ENTRYPOINT ["uv", "run", "scenarios/opencaptchaworld/opencaptchaworld_judge.py"]
CMD ["--host", "0.0.0.0", "--port", "9010"]
