resource "google_bigquery_dataset" "rag" {
  project                    = local.project_id
  dataset_id                 = "rag"
  location                   = var.region
  delete_contents_on_destroy = false
  labels                     = var.labels
}

# Document chunks and their embeddings. Ingestion replaces the contents on each run.
resource "google_bigquery_table" "chunks" {
  project    = local.project_id
  dataset_id = google_bigquery_dataset.rag.dataset_id
  table_id   = "chunks"
  schema     = file("${path.module}/../ingest/schema/chunks.json")
  labels     = var.labels
}

# One row per evaluation run.
resource "google_bigquery_table" "eval_runs" {
  project    = local.project_id
  dataset_id = google_bigquery_dataset.rag.dataset_id
  table_id   = "eval_runs"
  schema     = file("${path.module}/../eval/schema/eval_runs.json")
  labels     = var.labels
}
