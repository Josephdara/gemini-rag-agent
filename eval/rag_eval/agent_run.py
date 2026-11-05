import time


async def ask(question):
    """Runs one question through the same agent Cloud Run serves, and returns its answer and every chunk its
    searches returned, in order."""
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from rag_agent.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="rag_eval")
    session = await runner.session_service.create_session(app_name="rag_eval", user_id="eval")
    message = types.Content(role="user", parts=[types.Part(text=question)])
    retrieved, answer = [], ""
    start = time.monotonic()
    async for event in runner.run_async(user_id="eval", session_id=session.id, new_message=message):
        for response in event.get_function_responses():
            if response.name == "search_documents":
                retrieved.extend(response.response.get("results", []))
        if event.is_final_response() and event.content:
            answer = "".join(part.text or "" for part in event.content.parts or [] if not part.thought)
    return {"answer": answer, "retrieved": dedupe(retrieved), "seconds": time.monotonic() - start}


def dedupe(chunks):
    seen = set()
    unique = []
    for chunk in chunks:
        if chunk["citation"] not in seen:
            seen.add(chunk["citation"])
            unique.append(chunk)
    return unique
