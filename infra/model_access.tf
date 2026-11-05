locals {
  allowed_models = sort(distinct([
    for model in [var.chat_model, var.embedding_model, var.judge_model] : "publishers/google/models/${model}:predict"
  ]))
}

# Replaces the organization's allow-all with the models this project uses. It is set on this project only.
resource "google_org_policy_policy" "allowed_models" {
  name   = "projects/${google_project.this.number}/policies/vertexai.allowedModels"
  parent = "projects/${google_project.this.number}"

  spec {
    rules {
      values {
        allowed_values = local.allowed_models
      }
    }
  }

  depends_on = [terraform_data.apis_ready]
}
