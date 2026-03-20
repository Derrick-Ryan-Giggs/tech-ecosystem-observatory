import requests
import pandas as pd
from google.cloud import storage, bigquery
from google.oauth2 import service_account
from datetime import datetime, timezone

PROJECT_ID   = "tech-ecosystem-obs"
BUCKET_NAME  = "tech-ecosystem-obs-data-lake"
GCS_RAW_PATH = "raw/yc_companies/"
BQ_DATASET   = "raw"
BQ_TABLE     = "raw_yc_companies_partitioned"
YC_API_URL   = "https://yc-oss.github.io/api/companies/all.json"

credentials = service_account.Credentials.from_service_account_file("/app/credentials.json")

print("Fetching YC company data...")
df = pd.DataFrame(requests.get(YC_API_URL, timeout=30).json())
cols = ["id", "name", "slug", "all_locations", "website", "batch", "status", "industry", "tags", "team_size", "long_description"]
df = df[[c for c in cols if c in df.columns]]
df.columns = df.columns.str.strip().str.lower()
df["tags"] = df["tags"].apply(lambda x: ", ".join(x) if isinstance(x, list) else (x or ""))
df["long_description"] = df["long_description"].apply(lambda x: " ".join(str(x).split()) if pd.notna(x) else "")
df["ingested_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"Fetched {df.shape[0]} YC companies")

storage_client = storage.Client(credentials=credentials, project=PROJECT_ID)
bucket         = storage_client.bucket(BUCKET_NAME)
local_path     = "/tmp/yc_companies.jsonl"
df.to_json(local_path, orient="records", lines=True, force_ascii=False)
timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
blob_name = f"{GCS_RAW_PATH}yc_companies_{timestamp}.jsonl"
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
