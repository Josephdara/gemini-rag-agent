import pytest

from rag_agent.config import settings

TEST_ENV = {
    "GOOGLE_CLOUD_PROJECT": "test-project",
    "GOOGLE_CLOUD_LOCATION": "us",
    "CHAT_MODEL": "gemini-test",
    "EMBEDDING_MODEL": "embedding-test",
    "BQ_DATASET": "rag",
    "BQ_LOCATION": "us-east4",
    "TOP_K": "3",
    "MODEL_ARMOR_TEMPLATE": "projects/test-project/locations/us/templates/baseline",
}


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    """Every test sees the same fake project; nothing here reaches Google Cloud."""
    for name, value in TEST_ENV.items():
        monkeypatch.setenv(name, value)
    settings.cache_clear()
    yield settings()
    settings.cache_clear()
