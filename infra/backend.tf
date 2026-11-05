# State lives in the bucket that state.tf creates. For the bootstrap apply, before the bucket exists, copy
# bootstrap_override.tf.example to bootstrap_override.tf to use local state; the README has the steps.
terraform {
  backend "gcs" {
    prefix = "rag-agent"
  }
}
