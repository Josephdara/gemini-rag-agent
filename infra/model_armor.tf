locals {
  model_armor_template = "projects/${local.project_id}/locations/us/templates/${google_model_armor_template.baseline.template_id}"
}

# Floor setting that inspects and blocks wherever Agent Platform applies it. In tenantloom-ai testing it applied
# on the global endpoint but not on the us endpoint, so the agent also screens in the application.
resource "google_model_armor_floorsetting" "project" {
  parent                           = "projects/${local.project_id}"
  location                         = "global"
  enable_floor_setting_enforcement = true
  integrated_services              = ["AI_PLATFORM"]

  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "MEDIUM_AND_ABOVE"
    }

    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }

    sdp_settings {
      basic_config {
        filter_enforcement = "ENABLED"
      }
    }
  }

  ai_platform_floor_setting {
    inspect_and_block    = true
    enable_cloud_logging = true
  }
}

# Template the agent calls through the sanitize API for the prompt, retrieved chunks, and the response.
resource "google_model_armor_template" "baseline" {
  project     = local.project_id
  location    = "us"
  template_id = "baseline"

  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "MEDIUM_AND_ABOVE"
    }

    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }

    sdp_settings {
      basic_config {
        filter_enforcement = "ENABLED"
      }
    }
  }

  template_metadata {
    log_sanitize_operations = true
  }
}

# Agent Platform service agent, which Google otherwise creates only on first use.
resource "google_project_service_identity" "aiplatform" {
  provider = google-beta

  project = local.project_id
  service = "aiplatform.googleapis.com"
}

# Lets the Agent Platform service agent call Model Armor for the floor setting.
resource "google_project_iam_member" "aiplatform_agent_model_armor" {
  project = local.project_id
  role    = "roles/modelarmor.user"
  member  = google_project_service_identity.aiplatform.member
}
