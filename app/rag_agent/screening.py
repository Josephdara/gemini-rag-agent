"""Model Armor screening through the sanitize API.

Floor settings did not apply to Gemini calls on the us endpoint in tenantloom-ai testing, so the agent screens the
user's prompt, each retrieved chunk, and its final answer itself. A failed sanitize call raises, so screening fails
closed.
"""

from functools import cache

from .config import settings

BLOCKED_PROMPT = "I can't help with that request."
BLOCKED_RESPONSE = "I can't share that answer."

METHODS = {
    "prompt": ("sanitizeUserPrompt", "userPromptData"),
    "response": ("sanitizeModelResponse", "modelResponseData"),
}


@cache
def _session():
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return AuthorizedSession(credentials)


def sanitize_url(template, method):
    location = template.split("/")[3]
    return f"https://modelarmor.{location}.rep.googleapis.com/v1/{template}:{method}"


def flagged(text, kind, sess=None):
    """True when any filter in the template matches the text."""
    method, field = METHODS[kind]
    response = (sess or _session()).post(
        sanitize_url(settings().model_armor_template, method), json={field: {"text": text}}, timeout=30
    )
    response.raise_for_status()
    return response.json()["sanitizationResult"]["filterMatchState"] == "MATCH_FOUND"


def _text(content):
    # Tool results arrive as function_response parts, which carry no text.
    return "".join(part.text or "" for part in (content.parts or []) if not part.thought) if content else ""


def _reply(text):
    from google.adk.models import LlmResponse
    from google.genai import types

    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def screen_prompt(callback_context, llm_request):
    """Before each model call: blocks the turn if the user's latest message is flagged."""
    if not settings().model_armor_template or not llm_request.contents:
        return None
    last = llm_request.contents[-1]
    text = _text(last) if last.role == "user" else ""
    if text and flagged(text, "prompt"):
        return _reply(BLOCKED_PROMPT)
    return None


def screen_chunks(tool, args, tool_context, tool_response):
    """After a search: drops flagged chunks, since retrieved documents are a path for prompt injection."""
    if tool.name != "search_documents" or not settings().model_armor_template:
        return None
    results = tool_response["results"]
    kept = [result for result in results if not flagged(result["text"], "prompt")]
    return {"results": kept, "dropped_by_screening": len(results) - len(kept)}


def screen_response(callback_context, llm_response):
    """After each model call: replaces a flagged answer. Streamed partial text is not screened, so use /run."""
    if not settings().model_armor_template or llm_response.partial:
        return None
    text = _text(llm_response.content)
    if text and flagged(text, "response"):
        return _reply(BLOCKED_RESPONSE)
    return None
