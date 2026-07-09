"""Agent Engine — ReAct loop with tool calling and SSE streaming."""

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

from app.providers.base import BaseLLMProvider, LLMStreamChunk
from app.providers.deepseek_provider import DeepSeekProvider
from app.providers.fallback import CircuitBreakerProvider


@dataclass
class ToolCall:
    """Parsed tool call from LLM output."""
    name: str
    args: dict


@dataclass
class AgentStep:
    """One step in the ReAct loop."""
    phase: str  # "think" | "act" | "observe" | "respond"
    content: str
    tool_call: ToolCall | None = None
    tool_result: str | None = None


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    name: str = "AgentForge"
    system_prompt: str = "You are a helpful AI assistant."
    tools: list[dict] = field(default_factory=list)
    max_iterations: int = 5


class AgentEngine:
    """ReAct Agent loop with tool calling.

    Usage:
        engine = AgentEngine(llm=provider, config=AgentConfig(...))
        async for event in engine.run("user question"):
            yield event  # SSE event dict
    """

    def __init__(self, llm: BaseLLMProvider | None = None, config: AgentConfig | None = None):
        self.llm = llm or DeepSeekProvider()
        self.config = config or AgentConfig()
        self._tool_executor = _ToolExecutor()

    @staticmethod
    def _parse_tool_call(text: str) -> ToolCall | None:
        """Extract tool call JSON from model output."""
        m = re.search(
            r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"args"\s*:\s*(\{[^}]+\})\s*\}',
            text,
        )
        if m:
            try:
                return ToolCall(name=m.group(1), args=json.loads(m.group(2)))
            except json.JSONDecodeError:
                pass
        return None

    async def run(self, user_message: str, history: list[dict] | None = None) -> AsyncIterator[dict]:
        """Run the ReAct agent loop, yielding SSE events."""
        trace_id = f"trace_{int(time.time()*1000)}"

        # Build messages
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        yield {"event": "start", "trace_id": trace_id, "agent": self.config.name}

        # ReAct loop
        for iteration in range(self.config.max_iterations):
            # ---- THINK ----
            yield {"event": "phase", "phase": "think", "iteration": iteration + 1}

            full_response = ""
            tool_call = None

            async for chunk in self.llm.chat_stream(messages):
                yield {"event": "token", "content": chunk.content}
                full_response += chunk.content

            # Parse tool call
            tool_call = self._parse_tool_call(full_response)

            if not tool_call:
                # No tool call — this is the final answer
                yield {"event": "phase", "phase": "respond"}
                yield {"event": "done", "trace_id": trace_id, "iterations": iteration + 1}
                return

            # ---- ACT ----
            yield {"event": "phase", "phase": "act", "tool": tool_call.name}

            tool_result = self._tool_executor.execute(tool_call)
            yield {
                "event": "tool_result",
                "tool": tool_call.name,
                "args": tool_call.args,
                "result": tool_result,
            }

            # ---- OBSERVE ----
            messages.append({"role": "assistant", "content": full_response})
            messages.append({
                "role": "user",
                "content": f'<tool_result name="{tool_call.name}">\n{tool_result}\n</tool_result>',
            })

        # Max iterations reached
        yield {"event": "phase", "phase": "respond"}
        yield {"event": "done", "trace_id": trace_id, "max_iterations": True}

    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool definitions."""
        lines = [self.config.system_prompt]
        if self.config.tools:
            lines.append("\n## Available Tools")
            lines.append('Call tools using: {"tool": "tool_name", "args": {...}}')
            for t in self.config.tools:
                params = ", ".join(
                    f"{k}: {v.get('description', v.get('type', ''))}"
                    for k, v in t.get("parameters", {}).get("properties", {}).items()
                )
                lines.append(f"- **{t['name']}**: {t['description']}")
                lines.append(f"  Params: {params}")
        return "\n".join(lines)


class _ToolExecutor:
    """Executes tool calls. Extensible registry."""

    def __init__(self):
        self._tools = {}

    def register(self, name: str, fn, schema: dict | None = None):
        self._tools[name] = fn

    def execute(self, tool_call: ToolCall) -> str:
        fn = self._tools.get(tool_call.name)
        if fn is None:
            return f"Unknown tool: {tool_call.name}"
        try:
            return str(fn(**tool_call.args))
        except Exception as e:
            return f"Tool error ({tool_call.name}): {e}"


# ---- Singleton engine factory ----

_default_engine: AgentEngine | None = None


def get_agent_engine() -> AgentEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = AgentEngine()
    return _default_engine


def get_engine_with_tools(tools: list[dict]) -> AgentEngine:
    """Create an engine with registered tools from definitions."""
    engine = AgentEngine()
    return engine
