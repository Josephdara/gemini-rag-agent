"""ADK API server for Cloud Run, plus a one-page chat UI at /. It serves rag_agent from this folder; the ADK web UI
is off. On Cloud Run, IAP signs users in before any request reaches this app."""

import os
from pathlib import Path

import uvicorn
from fastapi.responses import FileResponse
from google.adk.cli.fast_api import get_fast_api_app

HERE = Path(__file__).resolve().parent

# Sessions live in memory, here and on Cloud Run, so no session file is written next to the agent. A request that
# lands on another instance starts a new session instead of failing.
app = get_fast_api_app(agents_dir=str(HERE), web=False, use_local_storage=False, auto_create_session=True)


@app.get("/", include_in_schema=False)
def chat_page():
    return FileResponse(HERE / "static" / "index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
