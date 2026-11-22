"""LLM client for any OpenAI-compatible chat API with tool calling.

Free providers that speak this protocol include Groq, Google Gemini (OpenAI-compatible endpoint),
OpenRouter (free models) and local servers such as Ollama. Switching provider is a config change.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    message: dict = field(default_factory=dict)  # assistant message, replayable as-is
    finish_reason: str | None = None


class LLM(Protocol):
    def complete(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 1500,
    ) -> LLMResponse: ...


class OpenAICompatibleLLM:
    def __init__(self, model: str, base_url: str, api_key: str | None, max_retries: int = 3):
        from openai import OpenAI  # lazy import so the package loads without the dependency

        # Local servers such as Ollama ignore the key but the client requires a non-empty value.
        clean_key = (api_key or "").strip()
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        if not clean_key and not is_local:
            raise ValueError(
                "LLM_API_KEY is missing or empty. Please set your API key in .env or provide LLM_API_KEY."
            )

        self.client = OpenAI(base_url=base_url, api_key=clean_key or "not-needed")
        self.model = model
        self.max_retries = max_retries

    def complete(self, system, messages, tools=None, max_tokens=1500) -> LLMResponse:
        payload = [{"role": "system", "content": system}, *messages]
        kwargs = dict(model=self.model, messages=payload, max_tokens=max_tokens)
        if tools:
            kwargs["tools"] = tools
        resp = self._call(kwargs)

        choice = resp.choices[0]
        msg = choice.message
        calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}  # the agent reports the bad call back to the model via the tool result
            calls.append(ToolCall(id=tc.id, name=tc.function.name, input=args))

        message = {"role": "assistant", "content": msg.content or ""}
        if calls:
            message["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.name, "arguments": json.dumps(c.input)}}
                for c in calls
            ]
        return LLMResponse(text=msg.content or "", tool_calls=calls,
                           message=message, finish_reason=choice.finish_reason)

    def _call(self, kwargs):
        from openai import AuthenticationError, RateLimitError

        # Free tiers are rate limited; back off and retry instead of failing the turn.
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.chat.completions.create(**kwargs)
            except AuthenticationError as e:
                masked = (
                    f"{self.client.api_key[:6]}...{self.client.api_key[-4:]}"
                    if len(self.client.api_key) > 10
                    else repr(self.client.api_key)
                )
                raise RuntimeError(
                    f"Authentication failed (401) with {self.client.base_url} using key {masked}.\n"
                    "Please check your LLM_API_KEY in .env. If you previously set LLM_API_KEY in your shell, "
                    "clear it with: Remove-Item Env:LLM_API_KEY"
                ) from e
            except RateLimitError:
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt * 2)
