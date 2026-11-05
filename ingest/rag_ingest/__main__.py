"""Chunks, embeds, and indexes a folder of documents: python -m rag_ingest ingest/sample_docs"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rag_agent.config import settings
from rag_agent.embeddings import embed

from .chunking import chunk_text, read_documents

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "chunks.json"


def build_rows(documents, size, overlap, embed_fn, embedding_model, now):
    pieces = [
        (source, index, text)
        for source, document in documents
        for index, text in enumerate(chunk_text(document, size, overlap))
    ]
    vectors = embed_fn([text for _, _, text in pieces], "RETRIEVAL_DOCUMENT")
    return [
        {
            "chunk_id": f"{source}#{index}",
            "source": source,
            "chunk_index": index,
            "text": text,
            "embedding": vector,
            "embedding_model": embedding_model,
            "ingested_at": now.isoformat(),
        }
        for (source, index, text), vector in zip(pieces, vectors, strict=True)
    ]


def load(rows, client, table):
    """Replaces the table's contents with rows in one load job, so a failed run leaves the previous index."""
    from google.cloud import bigquery

    schema = [bigquery.SchemaField.from_api_repr(field) for field in json.loads(SCHEMA.read_text())]
    job_config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
    client.load_table_from_json(rows, table, job_config=job_config).result()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=100)
    args = parser.parse_args(argv)

    from google.cloud import bigquery

    s = settings()
    documents = list(read_documents(args.folder))
    if not documents:
        parser.error(f"no .md or .txt files in {args.folder}")
    rows = build_rows(documents, args.chunk_size, args.overlap, embed, s.embedding_model, datetime.now(timezone.utc))
    load(rows, bigquery.Client(project=s.project, location=s.bq_location), s.chunks_table)
    print(f"indexed {len(rows)} chunks from {len(documents)} documents into {s.chunks_table}")


if __name__ == "__main__":
    main()
