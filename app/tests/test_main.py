import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402


def test_chat_page_is_served_at_the_root():
    response = TestClient(main.app).get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '"rag_agent"' in response.text


def test_chat_page_never_inserts_text_as_html():
    page = (Path(main.__file__).parent / "static" / "index.html").read_text()
    assert "innerHTML" not in page
    assert "insertAdjacentHTML" not in page
    assert 'fetch("run"' in page  # /run, which screens complete responses, not /run_sse


def test_only_the_rag_agent_is_listed():
    assert TestClient(main.app).get("/list-apps").json() == ["rag_agent"]
