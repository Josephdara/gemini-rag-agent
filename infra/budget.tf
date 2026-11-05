locals {
  alert_thresholds = [0.5, 0.9, 1.0]
}

# Email channel that receives budget alerts.
resource "google_monitoring_notification_channel" "budget_email" {
  project      = local.project_id
  display_name = "RAG agent budget alerts"
  type         = "email"
  user_labels  = var.labels

  labels = {
    email_address = var.budget_alert_email
  }
}

# Monthly budget for this project; alerts only, nothing stops spend.
resource "google_billing_budget" "project" {
  billing_account = var.billing_account
  display_name    = "RAG agent (${var.project_id})"

  budget_filter {
    projects = ["projects/${google_project.this.number}"]
  }

  amount {
    specified_amount {
      units = tostring(var.budget_amount)
    }
  }

  dynamic "threshold_rules" {
    for_each = local.alert_thresholds
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [google_monitoring_notification_channel.budget_email.id]
  }
}
