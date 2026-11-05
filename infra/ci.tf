locals {
  github = var.github == null ? toset([]) : toset(["repo"])

  # Read access for planning this project, without job creation, log-entry reads, or secret access.
  plan_reader_permissions = [
    "artifactregistry.repositories.get",
    "artifactregistry.repositories.getIamPolicy",
    "bigquery.datasets.get",
    "bigquery.datasets.getIamPolicy",
    "bigquery.tables.get",
    "bigquery.tables.getIamPolicy",
    "cloudbuild.builds.get",
    "cloudbuild.builds.list",
    "cloudbuild.connections.get",
    "cloudbuild.repositories.get",
    "iam.roles.get",
    "iam.roles.list",
    "iam.serviceAccounts.get",
    "iam.serviceAccounts.getIamPolicy",
    "iam.serviceAccounts.list",
    "monitoring.notificationChannels.get",
    "monitoring.notificationChannels.list",
    "resourcemanager.projects.get",
    "resourcemanager.projects.getIamPolicy",
    "run.services.get",
    "run.services.getIamPolicy",
    "serviceusage.services.get",
    "serviceusage.services.list",
    "storage.buckets.get",
    "storage.buckets.getIamPolicy",
    "storage.buckets.list",
  ]
}

# Plans pull requests with read-only access. There is no apply identity; applies run locally.
resource "google_service_account" "terraform_plan" {
  project      = local.project_id
  account_id   = "sa-terraform-plan"
  display_name = "Terraform read-only plan"
}

resource "google_project_iam_custom_role" "plan_reader" {
  project     = local.project_id
  role_id     = "terraformPlanReader"
  title       = "Terraform plan reader"
  permissions = local.plan_reader_permissions
}

# Predefined read roles for what the custom role cannot cover, logs for the build, and quota for the budget
# and org policy APIs.
resource "google_project_iam_member" "terraform_plan" {
  # Static keys, because the custom role's name is known only after apply.
  for_each = {
    plan_reader          = google_project_iam_custom_role.plan_reader.name
    log_writer           = "roles/logging.logWriter"
    floor_setting_viewer = "roles/modelarmor.floorSettingsViewer"
    model_armor_viewer   = "roles/modelarmor.viewer"
    org_policy_viewer    = "roles/orgpolicy.policyViewer"
    quota_consumer       = "roles/serviceusage.serviceUsageConsumer"
  }

  project = local.project_id
  role    = each.value
  member  = google_service_account.terraform_plan.member
}

# Reads the budget.
resource "google_billing_account_iam_member" "terraform_plan" {
  billing_account_id = var.billing_account
  role               = "roles/billing.viewer"
  member             = google_service_account.terraform_plan.member

  # The Cloud Billing API must be enabled in the quota project first.
  depends_on = [terraform_data.apis_ready]
}

# Reads state and the CI inputs; -lock=false keeps it from writing a lock.
resource "google_storage_bucket_iam_member" "terraform_plan_state" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.terraform_plan.member
}

# Authorizing the connection stores the GitHub token through the Cloud Build service agent.
resource "google_project_iam_member" "cloudbuild_agent_secrets" {
  for_each = local.github

  project = local.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:service-${google_project.this.number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
}

# GitHub connection, created and authorized in the console, then imported.
resource "google_cloudbuildv2_connection" "github" {
  for_each = local.github

  project  = local.project_id
  location = var.region
  name     = var.github.connection_name

  github_config {
    app_installation_id = var.github.app_installation_id

    authorizer_credential {
      oauth_token_secret_version = var.github.oauth_token_secret_version
    }
  }

  depends_on = [google_project_iam_member.cloudbuild_agent_secrets]
}

resource "google_cloudbuildv2_repository" "repo" {
  for_each = local.github

  project           = local.project_id
  location          = var.region
  name              = "gemini-rag-agent"
  parent_connection = google_cloudbuildv2_connection.github[each.key].name
  remote_uri        = var.github.repo_uri
}

# Tests, security scans, and a read-only plan for each pull request to main.
resource "google_cloudbuild_trigger" "pr_check" {
  for_each = local.github

  project         = local.project_id
  location        = var.region
  name            = "pr-check"
  service_account = google_service_account.terraform_plan.id
  filename        = "cloudbuild/pr-check.yaml"
  substitutions   = { _STATE_BUCKET = google_storage_bucket.state.name }

  repository_event_config {
    repository = google_cloudbuildv2_repository.repo[each.key].id

    pull_request {
      branch          = "^main$"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }
}
