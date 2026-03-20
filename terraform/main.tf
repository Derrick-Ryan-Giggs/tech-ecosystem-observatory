terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file(var.credentials)
}

# GCS Bucket - Data Lake
resource "google_storage_bucket" "data_lake" {
  name          = "${var.project_id}-data-lake"
  location      = var.region
  force_destroy = true

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 90 }
  }
}

# BigQuery Datasets
resource "google_bigquery_dataset" "raw" {
  dataset_id = "raw"
  location   = var.region
}

resource "google_bigquery_dataset" "staging" {
  dataset_id = "staging"
  location   = var.region
}

resource "google_bigquery_dataset" "mart" {
  dataset_id = "mart"
  location   = var.region
}
