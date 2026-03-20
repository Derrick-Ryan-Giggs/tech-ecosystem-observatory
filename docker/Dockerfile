FROM python:3.11-slim
RUN pip install --no-cache-dir \
    google-cloud-storage \
    google-cloud-bigquery \
    google-cloud-bigquery-storage \
    google-auth \
    pandas \
    pyarrow \
    requests
WORKDIR /app
COPY credentials.json .
COPY ingest_layoffs.py .
COPY ingest_yc.py .
COPY verify.py .
