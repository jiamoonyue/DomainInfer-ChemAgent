"""Agent Engine — 设计文档 5.2 的 LangGraph StateGraph 实现。

流程: START → route_query → classify → think → [tool?] → execute_tool → observe → think → respond → END

同时接入：
  - 工具注册（从 TOOL_DEFINITIONS 注册到执行器）
  - RAG 上下文检索（Think 阶段前注入知识库内容）
  - Provider 熔断降级（CircuitBreakerProvider）
"""

import json
import re
import time
from typing import Any, AsyncIterator, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.providers.base import BaseLLMProvider, LLMResponse
from app.providers.litellm_provider import LiteLLMProvider
from app.providers.fallback import CircuitBreakerProvider
from app.modules.tools.engine import execute_tool, TOOL_DEFINITIONS


# ============================================================
# State Definition (LangGraph)
# ============================================================

class AgentState(TypedDict):
    """LangGraph state — holds the full conversation context."""
    messages: list[dict]
    tool_call: dict | None
    tool_result: str | None
    rag_context: str
    iteration: int
    final_answer: str
    agent_name: str
    agent_type: str  # "calculation" | "safety" | "knowledge" | "process"


# ============================================================
# Tool Executor (wraps engine tools)
# ============================================================

class ToolExecutor:
    """Executes registered tools. All tools from TOOL_DEFINITIONS auto-register."""

    def __init__(self):
        self._registry: dict[str, dict] = {}

    def register(self, name: str, fn, schema: dict | None = None):
        self._registry[name] = {"fn": fn, "schema": schema or {}}

    def execute(self, name: str, args: dict) -> str:
        entry = self._registry.get(name)
        if entry is None:
            return f"Unknown tool: {name}"
        try:
            return str(entry["fn"](**args))
        except Exception as e:
            return f"Tool error ({name}): {e}"

    def get_tool_prompt(self) -> str:
        """Generate the tool definitions section for the system prompt."""
        if not self._registry:
            return ""
        lines = ["\n## Available Tools"]
        lines.append('Call tools using: {"tool": "tool_name", "args": {...}}')
        for name, entry in self._registry.items():
            schema = entry["schema"]
            params = schema.get("parameters", {}).get("properties", {})
            desc = schema.get("description", "")
            params_str = ", ".join(
                f"{k}: {v.get('description', v.get('type', ''))}"
                for k, v in params.items()
            )
            lines.append(f"- **{name}**: {desc}")
            lines.append(f"  Params: {params_str}")
        return "\n".join(lines)


# Build the default tool executor with all built-in tools
_default_executor = ToolExecutor()
for td in TOOL_DEFINITIONS:
    from app.modules.tools.engine import TOOL_FUNCTIONS
    fn = TOOL_FUNCTIONS.get(td["name"])
    if fn:
        _default_executor.register(td["name"], fn, {
            "parameters": td["input_schema"],
            "description": td["description"],
        })


# ============================================================
# RAG Context Builder
# ============================================================

async def _build_rag_context(query: str, namespace: str = "chem") -> str:
    """Retrieve RAG context for the agent. Returns formatted context string."""
    try:
        from app.modules.rag.service import RAGService
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as sess:
            svc = RAGService(sess)
            docs = await svc.search(query, namespace, top_k=3)
            if not docs:
                return ""

            parts = ["\n## Knowledge Base Context (internal reference)"]
            for i, d in enumerate(docs, 1):
                parts.append(f"\n--- Source {i}: {d.get('source', 'unknown')} (score={d.get('score', 0):.2f}) ---\n{d['content'][:500]}")
            parts.append("\nBase your answer on the above context when applicable.")
            return "\n".join(parts)
    except Exception:
        return ""  # RAG unavailable — proceed without context


# ============================================================
# LLM Provider Factory
# ============================================================

def _build_provider(model_str: str | None = None) -> BaseLLMProvider:
    """Build the LLM provider with circuit breaker fallback.

    双重策略: API 失败 → 自动切换本地模型 (Ollama)

    设计文档 5.2:
      self.primary = LiteLLM(model="deepseek/deepseek-chat")  # 主模型(API)
      self.fallback1 = LiteLLM(model="ollama/qwen3:8b")       # 备选(本地,零成本)
    """
    primary = LiteLLMProvider(model=model_str or f"deepseek/{settings.DEEPSEEK_MODEL}")

    # Ollama local model as the actual fallback — no API key needed, zero cost
    ollama_fallback = LiteLLMProvider(model=f"ollama/{settings.LOCAL_MODEL_NAME}")

    return CircuitBreakerProvider(
        providers=[primary, ollama_fallback],
        failure_threshold=2,      # API 失败 2 次后熔断
        cooldown_seconds=30.0,    # 30 秒后重试 API
    )


# ============================================================
# LangGraph Node Functions
# ============================================================

def _parse_tool_call(text: str) -> dict | None:
    """Extract tool call JSON from LLM output."""
    m = re.search(
        r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"args"\s*:\s*(\{[^}]+\})\s*\}',
        text,
    )
    if m:
        try:
            return {"name": m.group(1), "args": json.loads(m.group(2))}
        except json.JSONDecodeError:
            pass
    return None


class AgentGraph:
    """LangGraph-based Agent with ReAct loop, tools, RAG, and Multi-Agent routing.

    Design doc 5.2 flow:
      START → classify → think → [tool?] → execute_tool → observe → think → respond → END
    """

    # Agent routing keywords (from old ChemAgent + YAML configs)
    AGENT_KEYWORDS = {
        "calculation": ["计算", "calculate", "分子量", "换算", "convert", "雷诺", "reynolds",
                       "配平", "balance", "理想气体", "多少", "?", "换热器", "管径", "流速", "热负荷"],
        "safety": ["安全", "危险", "有毒", "msds", "safety", "hazard", "toxic",
                  "flammable", "explosive", "corrosive", "防护", "泄漏", "爆炸", "腐蚀", "ppe", "应急"],
        "process": ["设计", "design", "工艺", "process", "选型", "优化", "optimize",
                   "pfd", "pid", "流程图", "设备", "equipment", "精馏", "蒸馏"],
    }

    def __init__(self, provider: BaseLLMProvider, executor: ToolExecutor, agent_name: str = "AgentForge"):
        self.provider = provider
        self.executor = executor
        self.agent_name = agent_name
        self._graph = self._build_graph()

    def _classify_query(self, user_message: str) -> str:
        """Route query to the best agent type. Keyword-based (fast, deterministic)."""
        msg_lower = user_message.lower()
        scores = {}
        for agent_type, kws in self.AGENT_KEYWORDS.items():
            scores[agent_type] = sum(1 for kw in kws if kw in msg_lower)
            if agent_type in ("calculation", "process") and len(user_message.split()) <= 20:
                scores[agent_type] *= 1.5

        # Default to knowledge agent
        scores.setdefault("knowledge", 0.1)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if ranked[0][1] >= 2 and (len(ranked) == 1 or ranked[0][1] >= 2 * ranked[1][1]):
            return ranked[0][0]
        if ranked[0][1] > 0:
            return ranked[0][0]
        return "knowledge"

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(AgentState)

        builder.add_node("classify", self._classify_node)
        builder.add_node("think", self._think)
        builder.add_node("execute_tool", self._execute_tool)
        builder.add_node("respond", self._respond)

        builder.set_entry_point("classify")
        builder.add_edge("classify", "think")

        builder.add_conditional_edges(
            "think",
            self._route_after_think,
            {"execute_tool": "execute_tool", "respond": "respond"},
        )

        builder.add_edge("execute_tool", "think")
        builder.add_edge("respond", END)

        return builder.compile()

    def _classify_node(self, state: AgentState) -> AgentState:
        """Route the query to the right agent type."""
        user_msg = ""
        for m in reversed(state["messages"]):
            role = m["role"] if isinstance(m, dict) else getattr(m, "role", "")
            content = m["content"] if isinstance(m, dict) else getattr(m, "content", "")
            if role == "user":
                user_msg = content
                break

        agent_type = self._classify_query(user_msg)
        state["agent_type"] = agent_type

        # Adapt system prompt based on agent type
        if state["messages"] and isinstance(state["messages"][0], dict) and state["messages"][0]["role"] == "system":
            system = state["messages"][0]["content"]
            type_hints = {
                "calculation": "\n\n[You are acting as the Calculation Agent. Use tools for all numeric work.]",
                "safety": "\n\n[You are acting as the Safety Agent. Cite standards and give actionable advice.]",
                "knowledge": "\n\n[You are acting as the Knowledge Agent. Provide precise definitions and explanations.]",
                "process": "\n\n[You are acting as the Process Design Agent. Consider feasibility, economics, and safety.]",
            }
            system += type_hints.get(agent_type, "")
            state["messages"][0]["content"] = system

        return state

    async def _think(self, state: AgentState) -> AgentState:
        """LLM reasoning — generates response, may call a tool.

        Design doc flow: think node in LangGraph, produces assistant message or tool call.
        """
        iteration = state.get("iteration", 0) + 1

        # Inject RAG context on first iteration
        messages = list(state["messages"])  # plain list of dicts
        if iteration == 1:
            user_query = ""
            for m in reversed(messages):
                # Handle both dict and object messages
                role = m["role"] if isinstance(m, dict) else getattr(m, "role", "")
                content = m["content"] if isinstance(m, dict) else getattr(m, "content", "")
                if role == "user":
                    user_query = content
                    break

            rag_ctx = await _build_rag_context(user_query)
            if rag_ctx and messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
                messages[0]["content"] = messages[0]["content"] + rag_ctx

        # Normalize messages to dicts for the LLM provider
        normalized = []
        for m in messages:
            if isinstance(m, dict):
                normalized.append(m)
            else:
                normalized.append({
                    "role": getattr(m, "role", "user"),
                    "content": getattr(m, "content", ""),
                })

        response = await self.provider.chat(messages=normalized, temperature=0.7)

        assistant_msg = {"role": "assistant", "content": response.content}
        state["messages"] = list(state["messages"]) + [assistant_msg]
        state["iteration"] = iteration
        state["tool_call"] = _parse_tool_call(response.content)

        return state

    def _execute_tool(self, state: AgentState) -> AgentState:
        """Execute the parsed tool call. Design doc: act → observe."""
        tc = state.get("tool_call")
        if tc is None:
            state["tool_result"] = "Error: no tool call to execute"
            return state

        result = self.executor.execute(tc["name"], tc["args"])
        state["tool_result"] = result

        # Append tool result as a plain dict message (not LangChain Message)
        tool_name = tc["name"]
        tool_msg = {
            "role": "user",
            "content": f'<tool_result name="{tool_name}">\n{result}\n</tool_result>',
        }
        state["messages"] = list(state["messages"]) + [tool_msg]

        return state

    def _respond(self, state: AgentState) -> AgentState:
        """Set final answer from last assistant message."""
        for m in reversed(state["messages"]):
            role = m["role"] if isinstance(m, dict) else getattr(m, "role", "")
            content = m["content"] if isinstance(m, dict) else getattr(m, "content", "")
            if role == "assistant":
                state["final_answer"] = content
                break
        return state

    def _route_after_think(
        self, state: AgentState
    ) -> Literal["execute_tool", "respond"]:
        """Route: if tool was called, execute it; otherwise respond."""
        if state.get("tool_call") and state.get("iteration", 0) < 5:
            return "execute_tool"
        return "respond"

    def get_graph(self):
        return self._graph


# ============================================================
# Agent Engine — public API
# ============================================================

class AgentEngine:
    """Public API for running Agent conversations.

    Supports both synchronous (via graph.invoke) and streaming (poll-based SSE).
    """

    def __init__(
        self,
        agent_name: str = "AgentForge",
        tools: list[dict] | None = None,
        system_prompt: str | None = None,
        max_iterations: int = 5,
    ):
        self.agent_name = agent_name
        self.max_iterations = max_iterations

        self.provider = _build_provider()
        self.executor = _default_executor
        self.graph = AgentGraph(
            provider=self.provider,
            executor=self.executor,
            agent_name=agent_name,
        )
        self.system_prompt = system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        prompt = (
            f"You are {self.agent_name}, an enterprise AI Agent.\n\n"
            "You have access to tools and knowledge base context.\n"
            "- For calculations, ALWAYS use the provided tools — never guess numbers.\n"
            "- When knowledge base context is provided, reference it in your answer.\n"
            "- Use the user's language (Chinese or English).\n"
            "- Be accurate and concise.\n\n"
            "Tool call format:\n"
            '{"tool": "tool_name", "args": {"param1": "value1", ...}}\n'
        )
        prompt += self.executor.get_tool_prompt()
        return prompt

    async def run(self, user_message: str) -> AsyncIterator[dict]:
        """Run the Agent via LangGraph and yield SSE events (token-level streaming)."""
        trace_id = f"trace_{int(time.time() * 1000)}"

        yield {"event": "start", "trace_id": trace_id, "agent": self.agent_name}

        state: AgentState = {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            "tool_call": None,
            "tool_result": None,
            "rag_context": "",
            "iteration": 0,
            "final_answer": "",
            "agent_name": self.agent_name,
            "agent_type": "knowledge",
        }

        compiled = self.graph.get_graph()

        try:
            # Run LangGraph — use astream for node-by-node events
            async for chunk in compiled.astream(state):
                for node_name, node_output in chunk.items():
                    if node_name == "think":
                        # Report start of thinking
                        yield {"event": "phase", "phase": "think"}
                    elif node_name == "execute_tool":
                        tc = node_output.get("tool_call", {})
                        yield {
                            "event": "phase",
                            "phase": "act",
                            "tool": tc.get("name", ""),
                        }
                    elif node_name == "respond":
                        final_answer = node_output.get("final_answer", "")
                        # Token-level streaming of the final answer
                        if final_answer:
                            for char in final_answer:
                                yield {"event": "token", "content": char}

            # Get final state to report tool results
            final_state = await compiled.ainvoke(state)
            iterations = final_state.get("iteration", 0)
            tc = final_state.get("tool_call")
            tr = final_state.get("tool_result")

            if tc and iterations > 1:
                yield {
                    "event": "tool_result",
                    "tool": tc.get("name", ""),
                    "result": tr or "",
                }

            yield {
                "event": "done",
                "trace_id": trace_id,
                "iterations": iterations,
            }

        except Exception as e:
            yield {"event": "error", "message": str(e)}


# Singleton factory for the Agent chat endpoint
def get_agent_engine(agent_name: str = "AgentForge") -> AgentEngine:
    return AgentEngine(agent_name=agent_name)
