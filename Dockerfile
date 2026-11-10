FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYDANTIC_DISABLE_PLUGINS=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY v2 ./v2

RUN mkdir -p /app/data/mistakes

EXPOSE 8000

# Render injects PORT for web services. The fallback keeps local Docker use simple.
CMD uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000}
