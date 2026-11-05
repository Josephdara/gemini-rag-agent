output "project_number" {
  value = google_project.this.number
}

output "state_bucket" {
  value = google_storage_bucket.state.name
}

output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${local.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "build_service_account" {
  value = google_service_account.build.id
}

output "build_source_bucket" {
  value = google_storage_bucket.build_source.name
}

output "model_armor_template" {
  value = local.model_armor_template
}

output "agent_env" {
  value       = local.agent_env
  description = "Environment for running the agent, ingestion, and evaluation locally."
}

output "service_url" {
  value = try(google_cloud_run_v2_service.agent[0].uri, null)
}
