# Smallest permission set for calling allowlisted Gemini and embedding models.
resource "google_project_iam_custom_role" "gemini_invoker" {
  project     = local.project_id
  role_id     = "geminiInvoker"
  title       = "Gemini Invoker"
  description = "Call allowlisted publisher models"
  permissions = ["aiplatform.endpoints.predict"]
}

# Identity the Cloud Run service runs as.
resource "google_service_account" "runtime" {
  project      = local.project_id
  account_id   = "sa-rag-agent"
  display_name = "RAG agent runtime"
}

resource "google_project_iam_member" "runtime" {
  # Static keys, because the custom role's name is known only after apply.
  for_each = {
    gemini_invoker = google_project_iam_custom_role.gemini_invoker.name
    bigquery_jobs  = "roles/bigquery.jobUser"
    model_armor    = "roles/modelarmor.user"
  }

  project = local.project_id
  role    = each.value
  member  = google_service_account.runtime.member
}

# The agent only reads chunks.
resource "google_bigquery_dataset_iam_member" "runtime_reader" {
  project    = local.project_id
  dataset_id = google_bigquery_dataset.rag.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.runtime.member
}

# The operator runs ingestion and evaluation locally with their own credentials. aiplatform.user covers model
# calls and the evaluation service; serviceUsageConsumer lets this project be the operator's ADC quota project.
resource "google_project_iam_member" "operator" {
  for_each = toset([
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
    "roles/modelarmor.user",
    "roles/serviceusage.serviceUsageConsumer",
  ])

  project = local.project_id
  role    = each.value
  member  = var.operator_member
}

resource "google_bigquery_dataset_iam_member" "operator_editor" {
  project    = local.project_id
  dataset_id = google_bigquery_dataset.rag.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = var.operator_member
}
