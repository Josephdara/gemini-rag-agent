# The budget and org policy APIs need a quota project when Terraform runs with user credentials. It stays null
# for the bootstrap apply, before the project exists.
provider "google" {
  region = var.region

  user_project_override = var.quota_project != null
  billing_project       = var.quota_project
}

provider "google-beta" {
  region = var.region

  user_project_override = var.quota_project != null
  billing_project       = var.quota_project
}
