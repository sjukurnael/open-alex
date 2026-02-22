FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Run full load first, then start the API
CMD ["sh", "-c", "python load.py && uvicorn api:app --host 0.0.0.0 --port 8080"]
