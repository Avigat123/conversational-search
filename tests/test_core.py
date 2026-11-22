"""Offline tests: no API keys or network needed."""

from consearch.config import Settings
from consearch.llm import LLMResponse, ToolCall
from consearch.rag import RAGIndex, TfidfEmbedder, chunk_text
from consearch.search import SearchResult
from consearch.session import new_session
from consearch.sources import SourceRegistry, extract_citations


def _assistant(text="", calls=()):
    """Build a response the way OpenAICompatibleLLM does."""
    message = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": "{}"}} for c in calls
        ]
    return LLMResponse(text=text, tool_calls=list(calls), message=message)


class ScriptedLLM:
    """Returns pre-written responses in order and records what it was sent."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, system, messages, tools=None, max_tokens=1500):
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        return self.responses.pop(0)


class FakeWeb:
    def search(self, query, count=5):
        return [
            SearchResult("Paris - Wikipedia", "https://en.wikipedia.org/wiki/Paris",
                         "Paris is the capital and most populous city of France."),
            SearchResult("Paris population", "https://example.com/paris-pop",
                         "The population of Paris proper is about 2.1 million people."),
        ]


def test_chunking_overlaps_and_covers_text():
    words = [f"w{i}" for i in range(10)]
    chunks = chunk_text(" ".join(words), size=4, overlap=1)
    assert chunks[0].split() == ["w0", "w1", "w2", "w3"]
    assert chunks[1].split()[0] == "w3"  # overlap of one word
    assert chunks[-1].split()[-1] == "w9"  # last word is covered


def test_rag_retrieves_relevant_chunk():
    idx = RAGIndex(TfidfEmbedder(), chunk_words=50, chunk_overlap=0)
    idx.add_text("Photosynthesis converts sunlight into chemical energy in plants.", source_id=1)
    idx.add_text("The stock market closed higher after the Federal Reserve announcement.", source_id=2)
    hits = idx.search("how do plants use sunlight", k=1)
    assert hits and hits[0][0].source_id == 1


def test_citations_are_verified_and_unknown_markers_removed():
    reg = SourceRegistry()
    reg.add("A", "https://a.test")
    text, cited = extract_citations("Paris is the capital [1]. It is famous [7]. Also seen as 【1】 and 【1†source】.", reg)
    assert "[7]" not in text
    assert "[1]" in text
    assert "【" not in text
    assert [s.id for s in cited] == [1]


def test_agent_searches_then_answers_with_citations():
    call = ToolCall("t1", "web_search", {"query": "capital of France"})
    llm = ScriptedLLM([
        _assistant(calls=[call]),
        _assistant("Paris is the capital of France [1]. [9] is not a real source."),
    ])
    session = new_session(Settings(), llm=llm, web=FakeWeb())
    result = session.ask("What is the capital of France?")

    assert "[9]" not in result.text
    assert [s.url for s in result.sources] == ["https://en.wikipedia.org/wiki/Paris"]
    assert result.trace and result.trace[0].startswith("web_search")
    # The tool result returned to the model is a role=tool message with numbered sources.
    tool_msg = llm.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "t1"
    assert "[1] Paris - Wikipedia" in tool_msg["content"]


def test_follow_up_is_condensed_and_history_is_kept():
    llm = ScriptedLLM([
        _assistant("Paris is the capital of France."),                 # turn 1 answer
        _assistant("What is the population of Paris?"),                # turn 2 condense
        _assistant("About 2.1 million people live in Paris proper."),  # turn 2 answer
    ])
    session = new_session(Settings(), llm=llm, web=FakeWeb())
    session.ask("Tell me about France's capital.")
    session.ask("How many people live there?")

    condense_call = llm.calls[1]
    assert "Follow-up: How many people live there?" in condense_call["messages"][0]["content"]

    answer_call = llm.calls[2]
    assert answer_call["messages"][-1] == {"role": "user", "content": "What is the population of Paris?"}
    assert answer_call["messages"][0]["role"] == "user"
    assert len(session.history) == 4


def test_agent_forces_answer_when_budget_runs_out():
    settings = Settings(max_agent_steps=1)
    call = ToolCall("t", "search_memory", {"query": "x"})
    llm = ScriptedLLM([_assistant(calls=[call]), _assistant("Best effort answer.")])
    session = new_session(settings, llm=llm, web=FakeWeb())
    result = session.ask("anything")
    assert result.text == "Best effort answer."
    assert llm.calls[-1]["tools"] is None  # final call has no tools
