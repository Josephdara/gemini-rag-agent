# Versioned, soft-deleted bucket for Terraform state.
resource "google_storage_bucket" "state" {
  name                        = "${local.project_id}-tfstate"
  project                     = local.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = merge(var.labels, { purpose = "terraform-state" })

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 30
      # Otherwise the provider sends age = 0, which would delete live state objects.
      send_age_if_zero = false
    }
    action {
      type = "Delete"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# The pull request check reads these inputs at build time, so real IDs stay out of the repository.
resource "google_storage_bucket_object" "ci_config" {
  bucket       = google_storage_bucket.state.name
  name         = "config/terraform.tfvars.json"
  content_type = "application/json"
  content = jsonencode({
    org_id             = var.org_id
    billing_account    = var.billing_account
    project_id         = var.project_id
    region             = var.region
    quota_project      = var.quota_project
    operator_member    = var.operator_member
    app_users          = var.app_users
    chat_model         = var.chat_model
    embedding_model    = var.embedding_model
    judge_model        = var.judge_model
    gemini_location    = var.gemini_location
    embedding_location = var.embedding_location
    image              = var.image
    budget_amount      = var.budget_amount
    budget_alert_email = var.budget_alert_email
    github             = var.github
  })
}
