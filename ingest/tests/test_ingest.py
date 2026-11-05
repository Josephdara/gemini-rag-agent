import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from rag_ingest.__main__ import SCHEMA, build_rows
from rag_ingest.chunking import chunk_text, read_documents

SAMPLE_DOCS = Path(__file__).resolve().parent.parent / "sample_docs"


def test_short_text_is_one_chunk():
    assert chunk_text("  one short paragraph  ") == ["one short paragraph"]


def test_chunks_overlap_and_keep_words_whole():
    words = " ".join(f"word{i}" for i in range(400))
    chunks = chunk_text(words, size=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)
    vocabulary = set(words.split())
    assert all(set(chunk.split()) <= vocabulary for chunk in chunks)
    assert chunks[0].split()[-1] in chunks[1]


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_text("text", size=100, overlap=100)


def test_sample_docs_are_read_with_relative_sources():
    sources = [source for source, _ in read_documents(SAMPLE_DOCS)]
    assert sources == ["maintenance.md", "returns.md", "shipping.md", "warranty.md"]


def test_rows_match_the_chunks_table_schema():
    def fake_embed(texts, task_type):
        assert task_type == "RETRIEVAL_DOCUMENT"
        return [[0.0, 1.0] for _ in texts]

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = build_rows([("a.md", "alpha " * 400), ("b.md", "beta")], 1200, 200, fake_embed, "embedding-test", now)
    fields = {field["name"] for field in json.loads(SCHEMA.read_text())}
    assert all(set(row) == fields for row in rows)
    assert [row["chunk_id"] for row in rows] == ["a.md#0", "a.md#1", "a.md#2", "b.md#0"]
