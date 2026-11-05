# Agent container images.
resource "google_artifact_registry_repository" "images" {
  project       = local.project_id
  location      = var.region
  repository_id = "rag-agent"
  format        = "DOCKER"
  description   = "RAG agent images"

  docker_config {
    immutable_tags = true
  }
}

# Source archives uploaded by gcloud builds submit.
resource "google_storage_bucket" "build_source" {
  name                        = "${local.project_id}-build-source"
  project                     = local.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = var.labels

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }
}

# Builds images; holds no project-level storage or build roles.
resource "google_service_account" "build" {
  project      = local.project_id
  account_id   = "sa-build"
  display_name = "Image build"
}

resource "google_project_iam_member" "build_log_writer" {
  project = local.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.build.member
}

resource "google_storage_bucket_iam_member" "build_source_reader" {
  bucket = google_storage_bucket.build_source.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.build.member
}

resource "google_artifact_registry_repository_iam_member" "build_writer" {
  project    = local.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.repository_id
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.build.member
}

# Cloud Run pulls the image as the runtime identity.
resource "google_artifact_registry_repository_iam_member" "runtime_reader" {
  project    = local.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.repository_id
  role       = "roles/artifactregistry.reader"
  member     = google_service_account.runtime.member
}
