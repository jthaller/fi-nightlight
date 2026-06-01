FROM python:3.12-slim

RUN useradd --create-home appuser
WORKDIR /app

COPY pyproject.toml .
COPY fi_nightlight/ fi_nightlight/
COPY run.py .

RUN pip install --no-cache-dir ".[local]"

USER appuser
HEALTHCHECK --interval=60s --timeout=5s CMD pgrep -f run.py || exit 1

CMD ["python", "run.py"]
