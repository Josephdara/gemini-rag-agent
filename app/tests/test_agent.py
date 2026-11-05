from rag_agent import screening
from rag_agent.retrieval import search_documents


def test_agent_uses_the_search_tool_and_every_screen():
    from rag_agent.agent import root_agent

    assert root_agent.model == "gemini-test"
    assert root_agent.tools == [search_documents]
    assert root_agent.before_model_callback is screening.screen_prompt
    assert root_agent.after_tool_callback is screening.screen_chunks
    assert root_agent.after_model_callback is screening.screen_response
