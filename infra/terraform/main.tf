terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.25.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "random_id" "suffix" {
  byte_length = 4
}

# ── 1. Artifact Registry ─────────────────────────────────────────────
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "datareliant-${var.environment}"
  description   = "Docker container registry for DataReliant services"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    app         = "datareliant"
  }
}

# ── 2. Cloud Storage Bucket ──────────────────────────────────────────
resource "google_storage_bucket" "artifacts" {
  name                        = "datareliant-${var.environment}-${random_id.suffix.hex}"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    app         = "datareliant"
  }
}

# ── 3. BigQuery Analytics Dataset ────────────────────────────────────
resource "google_bigquery_dataset" "analytics" {
  dataset_id                  = "datareliant_${var.environment}"
  friendly_name               = "DataReliant Quality & Incident Warehouse"
  description                 = "Aggregated data quality profiles, anomalies, and incident telemetry"
  location                    = var.region
  default_table_expiration_ms = 31536000000 # 365 days

  labels = {
    environment = var.environment
    app         = "datareliant"
  }
}

# ── 4. Cloud Run Service Account ─────────────────────────────────────
resource "google_service_account" "api_sa" {
  account_id   = "datareliant-api-${var.environment}"
  display_name = "DataReliant API Service Account"
}

resource "google_storage_bucket_iam_member" "sa_storage_admin" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_bigquery_dataset_access" "sa_bq_access" {
  dataset_id    = google_bigquery_dataset.analytics.dataset_id
  role          = "roles/bigquery.dataEditor"
  user_by_email = google_service_account.api_sa.email
}

# ── 5. Cloud Run API Service ─────────────────────────────────────────
resource "google_cloud_run_v2_service" "api_service" {
  name     = "datareliant-api-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api_sa.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.api_image

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      ports {
        container_port = 8000
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.artifacts.name
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = google_bigquery_dataset.analytics.dataset_id
      }
      env {
        name  = "STORAGE_BACKEND"
        value = "gcs"
      }
    }
  }

  labels = {
    environment = var.environment
    app         = "datareliant"
  }
}

# Allow public unauthenticated invocation (or adjust for IAP)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.api_service.name
  location = google_cloud_run_v2_service.api_service.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
