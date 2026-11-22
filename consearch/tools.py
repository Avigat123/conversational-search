"""Tools the agent can call, and the shared workspace they operate on. Schemas use the OpenAI function format."""

from dataclasses import dataclass, field
from typing import Any

from .rag import RAGIndex
from .search import fetch_page
from .sources import SourceRegistry

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the public web. Returns numbered results with title, URL and snippet. "
                "Use for current events, external facts, or anything not already in memory."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "A concise search query."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Download and read a web page. Use a URL from web_search when the snippet is not enough.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "An http(s) URL."}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "Search passages already gathered in this conversation (earlier searches, pages and "
                "uploaded documents). Check this before searching the web again."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


@dataclass
class Workspace:
    """Everything that persists across turns of one conversation."""

    registry: SourceRegistry
    index: RAGIndex
    web: Any
    top_k: int = 5
    fetch_chars: int = 4000
    fetched: set[str] = field(default_factory=set)


class ToolRunner:
    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def run(self, name: str, args: dict) -> str:
        handlers = {
            "web_search": self._web_search,
            "fetch_page": self._fetch_page,
            "search_memory": self._search_memory,
        }
        if name not in handlers:
            return f"Unknown tool: {name}"
        try:
            return handlers[name](**args)
        except Exception as exc:  # errors go back to the model so it can recover
            return f"Tool '{name}' failed: {exc}"

    def _web_search(self, query: str) -> str:
        results = self.ws.web.search(query, count=self.ws.top_k)
        if not results:
            return "No web results found."
        lines = []
        for r in results:
            src = self.ws.registry.add(r.title, r.url, kind="web")
            if r.snippet:
                self.ws.index.add_text(f"{r.title}. {r.snippet}", src.id)
            lines.append(f"[{src.id}] {r.title}\nURL: {r.url}\nSnippet: {r.snippet}")
        return "\n\n".join(lines)

    def _fetch_page(self, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            return "Only http(s) URLs can be fetched."
        title, text = fetch_page(url)
        src = self.ws.registry.add(title, url, kind="web")
        if url not in self.ws.fetched:
            self.ws.index.add_text(text, src.id)
            self.ws.fetched.add(url)
        excerpt = text[: self.ws.fetch_chars]
        return f"[{src.id}] {src.title}\nURL: {url}\n\n{excerpt}"

    def _search_memory(self, query: str) -> str:
        hits = self.ws.index.search(query, k=self.ws.top_k)
        if not hits:
            return "No matching passages in memory."
        blocks = []
        for chunk, _score in hits:
            src = self.ws.registry.get(chunk.source_id)
            blocks.append(f"[{src.id}] {src.title} ({src.url})\n{chunk.text}")
        return "\n\n".join(blocks)
