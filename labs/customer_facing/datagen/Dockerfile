FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY *.sql .

CMD ["python", "/app/continuous_datagen.py"]
