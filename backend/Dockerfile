FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

# Use environment PORT (Cloud Run injects this)
CMD ["sh", "-c", "uvicorn server.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
