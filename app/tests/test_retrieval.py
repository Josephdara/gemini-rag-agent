from rag_agent import retrieval


class FakeQueryJob:
    def __init__(self, rows):
        self.rows = rows

    def result(self):
        return self.rows


class FakeBigQuery:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def query(self, sql, job_config=None):
        self.queries.append((sql, job_config))
        return FakeQueryJob(self.rows)


def fake_embed(texts, task_type):
    assert task_type == "RETRIEVAL_QUERY"
    return [[0.1, 0.2, 0.3] for _ in texts]


ROWS = [
    {"chunk_id": "faq.md#0", "source": "faq.md", "text": "first", "distance": 0.1},
    {"chunk_id": "faq.md#1", "source": "faq.md", "text": "second", "distance": 0.2},
]


def test_search_queries_the_chunks_table_with_the_query_embedding():
    client = FakeBigQuery(ROWS)
    results = retrieval.search("what?", client=client, embed_fn=fake_embed)
    sql, job_config = client.queries[0]
    assert "TABLE `test-project.rag.chunks`" in sql
    assert "top_k => 3" in sql
    [parameter] = job_config.query_parameters
    assert (parameter.name, parameter.values) == ("query_embedding", [0.1, 0.2, 0.3])
    assert [r["chunk_id"] for r in results] == ["faq.md#0", "faq.md#1"]


def test_tool_returns_citations_and_text_only(monkeypatch):
    monkeypatch.setattr(retrieval, "search", lambda query: ROWS)
    assert retrieval.search_documents("what?") == {
        "results": [{"citation": "faq.md#0", "text": "first"}, {"citation": "faq.md#1", "text": "second"}]
    }
