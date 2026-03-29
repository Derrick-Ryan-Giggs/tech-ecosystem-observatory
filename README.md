# Tech Ecosystem Observatory

> A cloud-native batch data pipeline analyzing global tech ecosystem health by correlating layoff trends with YC startup activity across industries and geographies.

![Architecture](images/architecture_diagram.png)

## Problem Description

The tech industry has experienced significant turbulence since 2022 — mass layoffs across major companies while new startups continue to emerge. This project builds an end-to-end data pipeline to answer:

- Which industries are shedding the most jobs?
- How do layoff trends correlate with YC startup activity by sector?
- Which countries and industries show the most ecosystem stress?
- Is there a relationship between how much funding a company raised and whether it laid off workers?

The result is a two-page Looker Studio dashboard that gives a clear picture of tech ecosystem health over time.

---

## Architecture

```
Kaggle CSV (layoffs)  ──┐
                        ├──► Kestra (batch orchestration) ──► GCS (data lake)
YC Companies API    ──┘                                          │
                                                                 ▼
                                              BigQuery (partitioned + clustered tables)
                                                                 │
                                                                 ▼
                                                    dbt Cloud (transformations)
                                                                 │
                                                                 ▼
                                                    Looker Studio (dashboard)
```

**Pipeline type:** Batch — runs weekly every Monday at 6AM UTC via Kestra scheduler.

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Infrastructure | Terraform | Provision GCS bucket and BigQuery datasets |
| Containerization | Docker | Package ingestion scripts into a portable image |
| Orchestration | Kestra v1.1.1 | Schedule and run batch ingestion pipeline |
| Data Lake | Google Cloud Storage | Store raw JSONL files |
| Data Warehouse | BigQuery | Partitioned and clustered analytical tables |
| Transformations | dbt Cloud | Staging views and mart tables |
| Visualization | Looker Studio | Two-page interactive dashboard |
| Version Control | GitHub | Source code and pipeline definitions |

---

## Data Sources

| Source | Description | Rows | Format |
|---|---|---|---|
| [Kaggle — swaptr/layoffs-2022](https://www.kaggle.com/datasets/swaptr/layoffs-2022) | Global tech layoffs 2022–2024 | 4,317 | CSV |
| [YC OSS API](https://yc-oss.github.io/api/companies/all.json) | All YC-backed companies | 5,690 | JSON (public API, no auth) |

### Sample API Response (YC Companies)

The YC Companies API returns a JSON array. Here is an example record:

```json
{
  "id": 1,
  "name": "Airbnb",
  "slug": "airbnb",
  "all_locations": "San Francisco, CA, USA",
  "website": "https://airbnb.com",
  "batch": "W09",
  "status": "Public",
  "industry": "Consumer",
  "tags": ["Travel", "Housing"],
  "team_size": 6132,
  "long_description": "Airbnb is an online marketplace for short-term homestays and experiences."
}
```

A sample response file is saved at `ingestion/yc_sample.json` for reference.

---

## Data Warehouse Design

### Tables

| Table | Layer | Type | Rows |
|---|---|---|---|
| `raw.raw_layoffs_partitioned` | Raw | Partitioned + Clustered | 4,317 |
| `raw.raw_yc_companies_partitioned` | Raw | Partitioned + Clustered | 5,690 |
| `dbt_ryanderrick_staging.stg_layoffs` | Staging | View | — |
| `dbt_ryanderrick_staging.stg_yc_companies` | Staging | View | — |
| `dbt_ryanderrick_mart.mart_monthly_layoffs` | Mart | Table | — |
| `dbt_ryanderrick_mart.mart_tech_ecosystem` | Mart | Table | — |

### Partitioning and Clustering Strategy

**`raw_layoffs_partitioned`**
- **Partitioned by:** `DATE_TRUNC(date, MONTH)`
  - Layoff data is primarily queried by time range — monthly trends, quarterly comparisons. Monthly partitioning means BigQuery only scans the relevant month's partitions instead of the full 4,317-row table, reducing both query time and cost.
- **Clustered by:** `industry`, `country`
  - The most common analytical queries filter or GROUP BY industry ("which sectors had the most layoffs?") and country ("US vs global comparison"). Clustering physically co-locates rows with the same industry/country values, making these filters significantly faster.

**`raw_yc_companies_partitioned`**
- **Partitioned by:** `DATE(ingested_at)`
  - Supports incremental refresh patterns — future pipeline runs can filter to recently ingested records only.
- **Clustered by:** `industry`, `status`
  - Dashboard queries frequently filter by industry sector and company status (Active, Acquired, Inactive). Clustering on these columns reduces bytes scanned.

---

## dbt Transformations

```
raw layer (BigQuery)
    └── staging (dbt views)
          ├── stg_layoffs          — cleans nulls, filters zero-layoff rows, standardizes columns
          └── stg_yc_companies     — cleans nulls, flattens tags, standardizes columns
    └── marts (dbt tables)
          ├── mart_monthly_layoffs — monthly aggregation by industry and country
          └── mart_tech_ecosystem  — industry-level join of layoffs + YC activity (stress ratio)
```

---

## Dashboard

Built in Looker Studio. Two pages:

**Page 1 — Layoffs Trends** (source: `mart_monthly_layoffs`)
- Time series: monthly layoffs over time (X: month, Y: total_laid_off)
- Bar chart: top 10 industries by total layoffs (X: industry, Y: total_laid_off)
- Geo map: layoffs by country
- Scorecard: total employees laid off
- Scorecard: total layoff events

**Page 2 — Ecosystem Health** (source: `mart_tech_ecosystem`)
- Bar chart: layoffs per YC company by industry — ecosystem stress ratio (X: industry, Y: layoffs_per_yc_company)
- Stacked bar: active vs acquired YC companies by industry (X: industry, Y: active_companies + acquired_companies)
- Table: full industry breakdown — layoffs, YC companies, stress ratio side by side
- Scorecard: total YC companies analyzed
- Scorecard: total industries covered

---

## Reproducing the Project

### Prerequisites

- GCP account with billing enabled
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed
- [Terraform](https://developer.hashicorp.com/terraform/install) installed
- [dbt Cloud](https://cloud.getdbt.com) account (free Developer tier)
- [Kaggle](https://www.kaggle.com) account for dataset download

### Step 1 — Clone the repo

```bash
git clone https://github.com/Derrick-Ryan-Giggs/tech-ecosystem-observatory.git
cd tech-ecosystem-observatory
```

### Step 2 — Set up GCP

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project — note the **Project ID**
3. Enable these APIs:
   - BigQuery API
   - Cloud Storage API
4. Create a service account:
   - Go to **IAM & Admin → Service Accounts → Create**
   - Name: `tech-obs-sa`
   - Grant roles: `BigQuery Admin`, `Storage Admin`
   - Create a JSON key and download it
5. Save the key:

```bash
mkdir -p ~/.gcp
mv ~/Downloads/your-key.json ~/.gcp/tech-obs-sa.json
```

### Step 3 — Provision infrastructure with Terraform

```bash
cd terraform

# Create tfvars file
cat > terraform.tfvars << EOF
project_id  = "YOUR_GCP_PROJECT_ID"
region      = "us-central1"
credentials = "~/.gcp/tech-obs-sa.json"
EOF

terraform init
terraform apply
```

This creates:
- GCS bucket: `YOUR_PROJECT_ID-data-lake`
- BigQuery datasets: `raw`, `staging`, `mart` (all in `us-central1`)

### Step 4 — Download the layoffs dataset

```bash
# Install Kaggle CLI
pip install kaggle

# Set up Kaggle credentials from https://www.kaggle.com/settings
mkdir -p ~/.kaggle
# Place your kaggle.json at ~/.kaggle/kaggle.json

# Download dataset
cd ingestion
kaggle datasets download -d swaptr/layoffs-2022 --unzip
mv layoffs.csv ingestion/layoffs.csv
```

Alternatively, the `layoffs.csv` file is included in the repo at `ingestion/layoffs.csv`.

### Step 5 — Upload layoffs CSV to GCS

```bash
gsutil cp ingestion/layoffs.csv gs://YOUR_PROJECT_ID-data-lake/raw/layoffs/layoffs.csv
```

### Step 6 — Build the Docker image

```bash
cd docker

# Copy your GCP credentials into the docker folder
cp ~/.gcp/tech-obs-sa.json credentials.json

# Build the image
docker build -t tech-obs-ingestion:v5 .
```

> **Note:** The credentials are baked into the image for local development. Do not push this image to a public registry.

### Step 7 — Start Kestra

```bash
cd kestra
docker compose up -d

# Wait for Kestra to be ready (~60 seconds)
docker compose logs -f kestra | grep -m1 "Server Running"
```

Open [http://localhost:8080](http://localhost:8080) and complete the account setup wizard.

### Step 8 — Register the Kestra flow

In the Kestra UI:
1. Go to **Flows → New Flow**
2. Paste the contents of `kestra/tech_observatory_flow.yml`
3. Save

Or via API (after account creation):

```bash
curl -s -X POST http://localhost:8080/api/v1/flows \
  -u "admin@admin.com:YOUR_PASSWORD" \
  -H "Content-Type: application/x-yaml" \
  --data-binary @kestra/tech_observatory_flow.yml
```

### Step 9 — Trigger the pipeline

In the Kestra UI:
1. Go to **Flows → tech_observatory_pipeline**
2. Click **Execute**
3. Monitor the execution — all 4 tasks should go green:
   - `ingest_layoffs` — loads 4,317 rows into BigQuery
   - `ingest_yc` — loads 5,690 rows into BigQuery
   - `verify_bigquery` — confirms both tables have data
   - `log_success` — logs completion timestamp

### Step 10 — Run dbt transformations

1. Create a free account at [cloud.getdbt.com](https://cloud.getdbt.com)
2. Create a new project connected to BigQuery:
   - Upload your service account JSON
   - Set **Location** to `us-central1`
3. Connect to the GitHub repo `Derrick-Ryan-Giggs/tech-ecosystem-observatory`
4. In the dbt Cloud IDE, run:

```
dbt run
```

This creates:
- `dbt_ryanderrick_staging.stg_layoffs` (view)
- `dbt_ryanderrick_staging.stg_yc_companies` (view)
- `dbt_ryanderrick_mart.mart_monthly_layoffs` (table)
- `dbt_ryanderrick_mart.mart_tech_ecosystem` (table)

### Step 11 — View the dashboard

1. Go to [lookerstudio.google.com](https://lookerstudio.google.com)
2. Create a new report
3. Connect to BigQuery → `YOUR_PROJECT_ID` → `dbt_ryanderrick_mart`
4. Add `mart_monthly_layoffs` and `mart_tech_ecosystem` as data sources
5. Build visualizations as described in the Dashboard section above

---

## Project Structure

```
tech-ecosystem-observatory/
├── docker/
│   ├── Dockerfile              # Docker image definition
│   ├── ingest_layoffs.py       # Layoffs ingestion script
│   ├── ingest_yc.py            # YC companies ingestion script
│   └── verify.py               # BigQuery verification script
├── ingestion/
│   ├── layoffs.csv             # Source layoffs data
│   ├── ingest_layoffs.py       # Local ingestion scripts
│   └── ingest_yc.py
├── kestra/
│   ├── docker-compose.yml      # Kestra + Postgres setup
│   └── tech_observatory_flow.yml  # Pipeline flow definition
├── models/
│   ├── staging/
│   │   ├── stg_layoffs.sql
│   │   ├── stg_yc_companies.sql
│   │   └── schema.yml
│   └── marts/
│       ├── mart_monthly_layoffs.sql
│       ├── mart_tech_ecosystem.sql
│       └── schema.yml
├── terraform/
│   ├── main.tf                 # GCS + BigQuery resources
│   └── variables.tf
├── images/
│   └── architecture_diagram.png
├── dbt_project.yml
└── README.md
```

---

## Evaluation Criteria Checklist

| Criterion | Implementation |
|---|---|
| Problem description | Clearly defined — correlating layoffs with YC startup activity |
| Cloud + IaC | GCP (BigQuery, GCS) provisioned with Terraform |
| Batch orchestration | Kestra end-to-end pipeline with weekly schedule |
| DWH partitioning + clustering | Both raw tables partitioned and clustered with explanation |
| dbt transformations | 4 models across staging and mart layers |
| Dashboard | 2-page Looker Studio dashboard with multiple tiles |
| Reproducibility | Step-by-step instructions from GCP setup to dashboard |

---

## Author

**Ryan Derrick Giggs**
- GitHub: [@Derrick-Ryan-Giggs](https://github.com/Derrick-Ryan-Giggs)
- Hashnode: [ryan-giggs.hashnode.dev](https://ryan-giggs.hashnode.dev)
- DEZ Zoomcamp 2026 Cohort
