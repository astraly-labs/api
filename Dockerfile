FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

ENV PATH="/root/.local/bin:${PATH}"

FROM base as builder

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
RUN uv sync --all-extras

FROM base as final
COPY --from=builder /opt /opt
WORKDIR /opt/pragma-api

# Expose the port that your application will listen on
EXPOSE 8007

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://0.0.0.0:8007/health || exit 1

# we need to run Uvicorn with the port 8007
CMD ["uvicorn", "pragma.main:app", "--host", "0.0.0.0", "--port", "8007"]
