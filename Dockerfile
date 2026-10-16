FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NOTES_API_DATABASE_URL=sqlite:////data/notes.db

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir . \
    && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin appuser \
    && mkdir /data \
    && chown appuser:appuser /data

USER appuser
VOLUME ["/data"]
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "notes_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
