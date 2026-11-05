variable "org_id" {
  type        = string
  description = "Organization that parents the project."
}

variable "billing_account" {
  type        = string
  description = "Billing account linked to the project, in the form XXXXXX-XXXXXX-XXXXXX."
}

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east4"
}

variable "quota_project" {
  type        = string
  default     = null
  description = "Project billed for API quota. Null for the bootstrap apply, then the project ID."
}

variable "operator_member" {
  type        = string
  description = "Person who runs ingestion and evaluation and calls the service, such as user:you@example.com."
}

variable "app_users" {
  type        = list(string)
  default     = []
  description = "People besides the operator who may use the chat page through IAP, such as user:name@example.com."
}

variable "labels" {
  type    = map(string)
  default = { app = "rag-agent" }
}

variable "chat_model" {
  type    = string
  default = "gemini-3.8-flash"
}

variable "embedding_model" {
  type    = string
  default = "gemini-embedding-001"
}

variable "judge_model" {
  type    = string
  default = "gemini-3.8-flash"
}

variable "gemini_location" {
  type        = string
  default     = "us"
  description = "Location the agent calls Gemini on; gemini-3.8-flash is served on us but not us-east4."
}

variable "embedding_location" {
  type        = string
  default     = "us-east4"
  description = "Location of the embedding model; gemini-embedding-001 is served on us-east4 but not us."
}

variable "image" {
  type        = string
  default     = null
  description = "Agent image. The Cloud Run service is created once this is set."
}

variable "budget_amount" {
  type        = number
  description = "Monthly budget in the billing account's currency."
}

variable "budget_alert_email" {
  type = string
}

variable "github" {
  type = object({
    connection_name            = string
    app_installation_id        = number
    oauth_token_secret_version = string
    repo_uri                   = string
  })
  default     = null
  description = "GitHub connection for the pull request check. Null until the connection is created and imported."
}
