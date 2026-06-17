FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so a code change does not rebuild this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

# Create tables if they are missing, then serve the API.
CMD ["sh", "-c", "python -m infra.init_db && uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
