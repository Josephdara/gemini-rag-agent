from functools import cache

from .config import settings
from .embeddings import embed

# Brute-force search is exact and needs no vector index at this size; add one past about 10k chunks.
SEARCH_SQL = """
SELECT base.chunk_id, base.source, base.text, distance
FROM VECTOR_SEARCH(
  TABLE `{table}`, 'embedding',
  (SELECT @query_embedding AS embedding),
  top_k => {top_k}, distance_type => 'COSINE'
)
ORDER BY distance
"""


@cache
def _bigquery(project, location):
    from google.cloud import bigquery

    return bigquery.Client(project=project, location=location)


def search(query, top_k=None, client=None, embed_fn=embed):
    """Returns the chunks closest to the query, nearest first."""
    from google.cloud import bigquery

    s = settings()
    top_k = int(top_k or s.top_k)
    client = client or _bigquery(s.project, s.bq_location)
    [vector] = embed_fn([query], "RETRIEVAL_QUERY")
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", vector)]
    )
    rows = client.query(SEARCH_SQL.format(table=s.chunks_table, top_k=top_k), job_config=job_config).result()
    return [
        {"chunk_id": row["chunk_id"], "source": row["source"], "text": row["text"], "distance": row["distance"]}
        for row in rows
    ]


def search_documents(query: str) -> dict:
    """Searches the indexed documents for passages relevant to the query.

    Args:
        query: What to look for, phrased as a short search query.

    Returns:
        The most relevant passages. Cite a passage by writing its citation in square brackets, such as [faq.md#0].
    """
    return {"results": [{"citation": r["chunk_id"], "text": r["text"]} for r in search(query)]}
