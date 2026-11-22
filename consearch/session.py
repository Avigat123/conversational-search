"""Conversation sessions: memory across turns, follow-up rewriting, and the public entry point."""

from pathlib import Path

from .agent import Agent, AgentResult
from .config import Settings
from .llm import LLM, OpenAICompatibleLLM
from .rag import RAGIndex, make_embedder
from .search import make_search
from .sources import Source, SourceRegistry
from .tools import Workspace

CONDENSE_PROMPT = """Rewrite the user's follow-up message as a standalone search question.
Use the conversation to resolve pronouns and references ("it", "that", "the second one", "more about this").
If the follow-up is already standalone, return it unchanged.
Return only the rewritten question, with no explanation."""


class ConversationSession:
    def __init__(self, llm: LLM, settings: Settings, workspace: Workspace):
        self.llm = llm
        self.settings = settings
        self.workspace = workspace
        self.agent = Agent(llm, settings)
        self.history: list[dict] = []  # alternating user / assistant messages

    @property
    def _recent_history(self) -> list[dict]:
        return self.history[-2 * self.settings.history_turns :]

    def ask(self, question: str) -> AgentResult:
        standalone = self._condense(question)
        result = self.agent.run(standalone, self._recent_history, self.workspace)
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": result.text})
        return result

    def ingest_file(self, path: str) -> Source:
        """Make a local .txt or .md file searchable by the agent."""
        p = Path(path)
        text = p.read_text(encoding="utf-8", errors="replace")
        src = self.workspace.registry.add(p.name, str(p.resolve()), kind="local")
        self.workspace.index.add_text(text, src.id)
        return src

    def _condense(self, question: str) -> str:
        if not self.history:
            return question
        transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in self._recent_history)
        resp = self.llm.complete(
            CONDENSE_PROMPT,
            [{"role": "user", "content": f"Conversation so far:\n{transcript}\n\nFollow-up: {question}"}],
            max_tokens=200,
        )
        return resp.text.strip() or question


def new_session(settings: Settings | None = None, llm: LLM | None = None, web=None) -> ConversationSession:
    settings = settings or Settings()
    llm = llm or OpenAICompatibleLLM(settings.model, settings.llm_base_url, settings.llm_api_key)
    web = web or make_search(settings.search_provider, settings.searxng_url)
    workspace = Workspace(
        registry=SourceRegistry(),
        index=RAGIndex(make_embedder(settings.embedder), settings.chunk_words, settings.chunk_overlap),
        web=web,
        top_k=settings.top_k,
        fetch_chars=settings.fetch_chars,
    )
    return ConversationSession(llm, settings, workspace)
