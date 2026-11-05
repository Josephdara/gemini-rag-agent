locals {
  apis = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iap.googleapis.com",
    "logging.googleapis.com",
    "modelarmor.googleapis.com",
    "monitoring.googleapis.com",
    "orgpolicy.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ])

  # Resources use this ID so they are created only after every API is enabled.
  project_id = terraform_data.apis_ready.output
}

# One project directly under the organization, outside the ai-platform folder.
resource "google_project" "this" {
  project_id          = var.project_id
  name                = var.project_id
  org_id              = var.org_id
  billing_account     = var.billing_account
  auto_create_network = false
  deletion_policy     = "PREVENT"
  labels              = var.labels
}

resource "google_project_service" "enabled" {
  for_each = local.apis

  project            = google_project.this.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "terraform_data" "apis_ready" {
  input      = google_project.this.project_id
  depends_on = [google_project_service.enabled]
}
