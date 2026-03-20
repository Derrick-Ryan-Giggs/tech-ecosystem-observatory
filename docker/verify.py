from google.cloud import bigquery
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file("/app/credentials.json")
client      = bigquery.Client(credentials=credentials, project="tech-ecosystem-obs")

for t in ["tech-ecosystem-obs.raw.raw_layoffs_partitioned", "tech-ecosystem-obs.raw.raw_yc_companies_partitioned"]:
    table = client.get_table(t)
    print(f"{t}: {table.num_rows} rows")
    if table.num_rows == 0:
        raise Exception(f"{t} is empty")
print("All tables verified successfully")
