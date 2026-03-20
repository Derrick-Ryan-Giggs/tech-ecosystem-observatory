import io
import pandas as pd
from google.cloud import storage, bigquery
from google.oauth2 import service_account
from datetime import datetime, timezone

PROJECT_ID   = "tech-ecosystem-obs"
BUCKET_NAME  = "tech-ecosystem-obs-data-lake"
GCS_CSV_PATH = "raw/layoffs/layoffs_20260312_115756.csv"
GCS_RAW_PATH = "raw/layoffs/"
BQ_DATASET   = "raw"
BQ_TABLE = "raw_layoffs_partitioned"

credentials = service_account.Credentials.from_service_account_file("/app/credentials.json")

print("Reading layoffs CSV from GCS...")
storage_client = storage.Client(credentials=credentials, project=PROJECT_ID)
bucket         = storage_client.bucket(BUCKET_NAME)
df             = pd.read_csv(io.BytesIO(bucket.blob(GCS_CSV_PATH).download_as_bytes()))
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
df["total_laid_off"]      = pd.to_numeric(df["total_laid_off"], errors="coerce").fillna(0).astype(int)
df["percentage_laid_off"] = pd.to_numeric(df["percentage_laid_off"], errors="coerce").fillna(0)
df["funds_raised"]        = pd.to_numeric(df["funds_raised"], errors="coerce").fillna(0)
df["location"]            = df["location"].fillna("Unknown")
df["industry"]            = df["industry"].fillna("Unknown")
df["country"]             = df["country"].fillna("Unknown")
df["stage"]               = df["stage"].fillna("Unknown")
df["source"]              = df["source"].fillna("Unknown")
df["date"]                = pd.to_datetime(df["date"], errors="coerce").astype(str)
df["date_added"]          = pd.to_datetime(df["date_added"], errors="coerce").astype(str)
df["ingested_at"]         = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"Loaded {len(df)} rows")

local_path = "/tmp/layoffs.jsonl"
df.to_json(local_path, orient="records", lines=True, force_ascii=False)
timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
blob_name = f"{GCS_RAW_PATH}layoffs_{timestamp}.jsonl"
bucket.blob(blob_name).upload_from_filename(local_path)
gcs_uri = f"gs://{BUCKET_NAME}/{blob_name}"
print(f"Uploaded to {gcs_uri}")

bq_client  = bigquery.Client(credentials=credentials, project=PROJECT_ID)
job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    autodetect=True,
)
job = bq_client.load_table_from_uri(gcs_uri, f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}", job_config=job_config)
job.result()
table = bq_client.get_table(f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}")
print(f"Loaded {table.num_rows} rows into {PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}")