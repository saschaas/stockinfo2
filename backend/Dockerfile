# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -e .

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Build argument for optional extras (e.g., "dagster")
ARG INSTALL_EXTRAS=""

# Install runtime dependencies including Playwright requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    wget \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r stockinfo && useradd -r -g stockinfo stockinfo

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels && \
    if [ -n "$INSTALL_EXTRAS" ]; then pip install --no-cache-dir ".[$INSTALL_EXTRAS]"; fi

# Install Playwright browsers in a system-wide location
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install chromium --with-deps && \
    chmod -R 755 /ms-playwright

# Copy application code
COPY backend/ ./backend/
COPY config/ ./config/
COPY agents/ ./agents/
COPY pipelines/ ./pipelines/

# Set ownership and make scripts executable
RUN chown -R stockinfo:stockinfo /app && \
    chmod +x /app/backend/scripts/*.sh

# Switch to non-root user
USER stockinfo

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
