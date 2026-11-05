from types import SimpleNamespace

import pytest
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from rag_agent import screening
from rag_agent.config import settings


class FakeResponse:
    def __init__(self, state):
        self.state = state

    def raise_for_status(self):
        pass

    def json(self):
        return {"sanitizationResult": {"filterMatchState": self.state}}


class FakeSession:
    """Flags any text that contains the marker."""

    def __init__(self, marker="CANARY"):
        self.marker = marker
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        text = next(iter(json.values()))["text"]
        return FakeResponse("MATCH_FOUND" if self.marker in text else "NO_MATCH_FOUND")


@pytest.fixture
def armor(monkeypatch):
    sess = FakeSession()
    monkeypatch.setattr(screening, "_session", lambda: sess)
    return sess


def user(text):
    return types.Content(role="user", parts=[types.Part(text=text)])


def model(text):
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def test_sanitize_url_uses_the_template_location():
    template = "projects/p/locations/us/templates/baseline"
    assert screening.sanitize_url(template, "sanitizeUserPrompt") == (
        "https://modelarmor.us.rep.googleapis.com/v1/projects/p/locations/us/templates/baseline:sanitizeUserPrompt"
    )


def test_flagged_prompt_is_blocked(armor):
    blocked = screening.screen_prompt(None, LlmRequest(contents=[user("CANARY please")]))
    assert blocked.content.parts[0].text == screening.BLOCKED_PROMPT
    assert screening.screen_prompt(None, LlmRequest(contents=[user("hello")])) is None
    assert armor.calls[0][1] == {"userPromptData": {"text": "CANARY please"}}


def test_tool_results_are_not_screened_as_prompts(armor):
    tool_turn = types.Content(
        role="user", parts=[types.Part.from_function_response(name="search_documents", response={"results": []})]
    )
    assert screening.screen_prompt(None, LlmRequest(contents=[user("hi"), tool_turn])) is None
    assert armor.calls == []


def test_flagged_chunks_are_dropped(armor):
    tool = SimpleNamespace(name="search_documents")
    response = {"results": [{"citation": "a.md#0", "text": "fine"}, {"citation": "b.md#0", "text": "CANARY"}]}
    screened = screening.screen_chunks(tool, {}, None, response)
    assert screened == {"results": [{"citation": "a.md#0", "text": "fine"}], "dropped_by_screening": 1}


def test_flagged_response_is_replaced(armor):
    assert screening.screen_response(None, model("CANARY")).content.parts[0].text == screening.BLOCKED_RESPONSE
    assert screening.screen_response(None, model("fine [a.md#0]")) is None
    assert armor.calls[0][1] == {"modelResponseData": {"text": "CANARY"}}


def test_screening_is_off_without_a_template(armor, monkeypatch):
    monkeypatch.setenv("MODEL_ARMOR_TEMPLATE", "")
    settings.cache_clear()
    assert screening.screen_prompt(None, LlmRequest(contents=[user("CANARY")])) is None
    assert armor.calls == []
