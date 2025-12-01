# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

ENV SERVER_PORT=8080
EXPOSE 8080

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"]
