"""Finds where the chat and embedding models are served for this project: uv run python scripts/probe_models.py

Makes one tiny request per model and location, one at a time, and prints which succeed. Set GOOGLE_CLOUD_LOCATION
and EMBEDDING_LOCATION (and gemini_location and embedding_location in Terraform) to a location that works.
"""

import os
import time

from google import genai

LOCATIONS = ["us-east4", "us"]


def try_call(call):
    try:
        call()
        return "ok"
    except Exception as error:
        return f"failed: {type(error).__name__}: {str(error)[:150]}"


def main():
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    chat_model = os.environ.get("CHAT_MODEL", "gemini-3.8-flash")
    embedding_model = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001")
    for location in LOCATIONS:
        client = genai.Client(vertexai=True, project=project, location=location)
        print(f"{chat_model} @ {location}:", try_call(lambda: client.models.generate_content(model=chat_model, contents="Say ok.")))
        time.sleep(2)
        print(f"{embedding_model} @ {location}:", try_call(lambda: client.models.embed_content(model=embedding_model, contents="ok")))
        time.sleep(2)


if __name__ == "__main__":
    main()
