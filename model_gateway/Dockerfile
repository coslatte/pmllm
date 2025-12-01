# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY model_gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY model_gateway /app/model_gateway

ENV MODEL_GATEWAY_PORT=9000
EXPOSE 9000

CMD ["uvicorn", "model_gateway.main:app", "--host", "0.0.0.0", "--port", "9000"]
