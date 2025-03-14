FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

ENV PATH="/root/.local/bin:${PATH}"

FROM base AS builder

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    gcc \
    curl \
    libgmp3-dev \
    pipx \
    && rm -rf /var/lib/apt/lists/*

RUN pipx install uv

COPY . /opt/pragma-api

WORKDIR /opt/pragma-api

# Install dependencies using pip
RUN pip install -e .

FROM base AS final

# Install runtime dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt /opt
COPY --from=builder /usr/local /usr/local

WORKDIR /opt/pragma-api

# Expose the port that your application will listen on
EXPOSE 8007

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://0.0.0.0:8007/health || exit 1

# Run using Python module to ensure proper PATH resolution
CMD ["python", "-m", "uvicorn", "pragma.main:app", "--host", "0.0.0.0", "--port", "8007"]
