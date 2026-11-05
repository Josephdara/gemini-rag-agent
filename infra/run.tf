locals {
  agent_env = {
    GOOGLE_GENAI_USE_VERTEXAI = "TRUE"
    GOOGLE_CLOUD_PROJECT      = local.project_id
    GOOGLE_CLOUD_LOCATION     = var.gemini_location
    CHAT_MODEL                = var.chat_model
    EMBEDDING_MODEL           = var.embedding_model
    EMBEDDING_LOCATION        = var.embedding_location
    BQ_DATASET                = google_bigquery_dataset.rag.dataset_id
    BQ_LOCATION               = var.region
    MODEL_ARMOR_TEMPLATE      = local.model_armor_template
  }
}

# The agent service and its chat page. Created once an image is built. IAP signs users in and is the only invoker.
resource "google_cloud_run_v2_service" "agent" {
  count = var.image == null ? 0 : 1

  project             = local.project_id
  name                = "rag-agent"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  iap_enabled         = true
  deletion_protection = false
  labels              = var.labels

  template {
    service_account = google_service_account.runtime.email
    # Keeps a browser's chat on one instance, since sessions live in memory.
    session_affinity = true

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      dynamic "env" {
        for_each = local.agent_env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  depends_on = [google_artifact_registry_repository_iam_member.runtime_reader]
}

# IAP service agent, which Google otherwise creates only on first use.
resource "google_project_service_identity" "iap" {
  provider = google-beta

  project = local.project_id
  service = "iap.googleapis.com"
}

# IAP calls the service as its service agent after checking the user; nobody else can invoke it.
resource "google_cloud_run_v2_service_iam_member" "iap_invoker" {
  count = var.image == null ? 0 : 1

  project  = local.project_id
  location = var.region
  name     = google_cloud_run_v2_service.agent[0].name
  role     = "roles/run.invoker"
  member   = google_project_service_identity.iap.member
}

# People IAP lets through to the chat page and API.
resource "google_iap_web_cloud_run_service_iam_member" "users" {
  for_each = var.image == null ? toset([]) : toset(concat([var.operator_member], var.app_users))

  project                = local.project_id
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.agent[0].name
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = each.value
}
