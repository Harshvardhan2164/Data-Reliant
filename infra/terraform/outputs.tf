output "api_service_url" {
  description = "Public HTTP endpoint for the Cloud Run DataReliant API service"
  value       = google_cloud_run_v2_service.api_service.uri
}

output "artifact_registry_repo" {
  description = "Docker repository URI in Artifact Registry"
  value       = "${google_artifact_registry_repository.docker_repo.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.name}"
}

output "gcs_bucket_name" {
  description = "Artifact and dataset storage bucket name"
  value       = google_storage_bucket.artifacts.name
}

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID for analytics telemetry"
  value       = google_bigquery_dataset.analytics.dataset_id
}
