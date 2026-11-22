"""Agentic search loop: the model decides what to search, when to stop, and what to cite."""

import json
from dataclasses import dataclass, field

from .config import Settings
from .llm import LLM
from .sources import Source, extract_citations
from .tools import TOOL_SCHEMAS, ToolRunner, Workspace

SYSTEM_PROMPT = """You are a research assistant that answers questions using evidence gathered with tools.

How to work:
- Call search_memory first to reuse evidence already gathered in this conversation.
- Call web_search for new or external information. Call fetch_page when a snippet is not enough.
- Stop searching as soon as you can answer confidently. Simple questions usually need 1 to 3 tool calls.
- If the question is a follow-up, rely on the conversation history to resolve references.

How to answer:
- Every claim taken from a source must end with that source's number in square brackets, such as [2] or [1][3].
- Only cite numbers that appeared in tool results. Never invent sources, numbers or URLs.
- If sources disagree, say so. If the evidence is insufficient, say what is missing instead of guessing.
- Lead with the direct answer, then give supporting detail. Be concise."""


@dataclass
class AgentResult:
    text: str
    sources: list[Source]
    steps: int
    trace: list[str] = field(default_factory=list)


class Agent:
    def __init__(self, llm: LLM, settings: Settings):
        self.llm = llm
        self.max_steps = settings.max_agent_steps

    def run(self, question: str, history: list[dict], workspace: Workspace) -> AgentResult:
        tools = ToolRunner(workspace)
        messages = [*history, {"role": "user", "content": question}]
        trace: list[str] = []

        for step in range(self.max_steps):
            resp = self.llm.complete(SYSTEM_PROMPT, messages, tools=TOOL_SCHEMAS)
            if not resp.tool_calls:
                return self._finish(resp.text, workspace, trace, step)

            messages.append(resp.message)
            for call in resp.tool_calls:
                trace.append(f"{call.name}({json.dumps(call.input, ensure_ascii=False)})")
                output = tools.run(call.name, call.input)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

        # Budget exhausted: force a final answer from what was gathered, with no more tools.
        messages.append({
            "role": "user",
            "content": "Research budget is used up. Answer now using only the evidence gathered so far.",
        })
        resp = self.llm.complete(SYSTEM_PROMPT, messages, tools=None)
        return self._finish(resp.text, workspace, trace, self.max_steps)

    @staticmethod
    def _finish(text: str, workspace: Workspace, trace: list[str], steps: int) -> AgentResult:
        cleaned, cited = extract_citations(text, workspace.registry)
        return AgentResult(text=cleaned.strip(), sources=cited, steps=steps, trace=trace)
