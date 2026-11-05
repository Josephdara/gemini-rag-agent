import pytest

from fakes import CONNECTION_ERROR, FakeResponse, FakeSession
from rag_eval import api
from rag_eval.api import ApiError, post_json


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)


def test_retries_transport_errors_and_transient_statuses():
    sess = FakeSession(CONNECTION_ERROR, FakeResponse(503, {}), FakeResponse(200, {"ok": True}))
    stats = {}
    assert post_json(sess, "https://x", {}, stats=stats) == {"ok": True}
    assert stats["attempts"] == 3


def test_does_not_retry_client_errors():
    sess = FakeSession(FakeResponse(400, {"error": "bad"}))
    with pytest.raises(ApiError):
        post_json(sess, "https://x", {})
    assert len(sess.calls) == 1


def test_gives_up_after_the_last_attempt():
    sess = FakeSession(*[FakeResponse(429, {})] * 3)
    with pytest.raises(ApiError):
        post_json(sess, "https://x", {}, attempts=3)


def test_api_host_handles_regional_multiregional_and_global():
    assert api.api_host("us-east4") == "https://us-east4-aiplatform.googleapis.com"
    assert api.api_host("us") == "https://aiplatform.us.rep.googleapis.com"
    assert api.api_host("global") == "https://aiplatform.googleapis.com"
