FROM python:3.12.10-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY services/api/pyproject.toml services/api/README.md services/api/requirements-runtime.lock ./
COPY services/api/src ./src
RUN python -m pip wheel --wheel-dir /wheels --requirement requirements-runtime.lock \
    && python -m pip wheel --wheel-dir /wheels --no-deps .

FROM python:3.12.10-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/momo/.local/bin:$PATH

RUN apt-get update \
    && apt-get install --no-install-recommends --yes tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system momo \
    && useradd --system --gid momo --create-home momo

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels
COPY services/api/migrations ./migrations
RUN mkdir -p /app/.local/private-storage \
    && chown -R momo:momo /app

USER momo
EXPOSE 8000
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=2", "--threads=2", "--timeout=60", "momo_fdvs.wsgi:app"]
