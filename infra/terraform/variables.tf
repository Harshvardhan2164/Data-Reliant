variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region for infrastructure deployment"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment identifier (e.g. dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "api_image" {
  description = "Container image URI for DataReliant API"
  type        = string
  default     = "us-central1-docker.pkg.dev/datareliant-prod/datareliant/api:latest"
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances (set > 0 to eliminate cold starts)"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "Cloud Run CPU allocation per container"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Cloud Run Memory allocation per container"
  type        = string
  default     = "4Gi"
}
