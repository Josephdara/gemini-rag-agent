from functools import cache

from .config import settings


@cache
def _client(project, location):
    from google import genai

    return genai.Client(vertexai=True, project=project, location=location)


def embed(texts, task_type):
    """Embeds each text with the configured Gemini embedding model.

    task_type is RETRIEVAL_DOCUMENT for chunks and RETRIEVAL_QUERY for questions, so both land in the same space.
    """
    from google.genai import types

    s = settings()
    client = _client(s.project, s.embedding_location)
    config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=s.embedding_dimensions)
    vectors = []
    # One text per request keeps each call inside the model's per-request input limit.
    for text in texts:
        response = client.models.embed_content(model=s.embedding_model, contents=text, config=config)
        vectors.append(list(response.embeddings[0].values))
    return vectors
