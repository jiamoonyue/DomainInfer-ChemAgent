"""MCP Tool Registry — sync DB tool definitions with in-memory executor.

Design doc 5.4: tools stored in DB, loaded into memory on startup.
"""

from app.modules.tools.engine import TOOL_DEFINITIONS, TOOL_FUNCTIONS


class ToolRegistry:
    """Synchronizes tool definitions between database and agent executor.

    Currently loads from built-in TOOL_DEFINITIONS (module-level constants).
    When PostgreSQL is available, seeds tool definitions from DB → memory.
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def load_from_definitions(self):
        """Load all built-in tool definitions into the registry."""
        for td in TOOL_DEFINITIONS:
            name = td["name"]
            fn = TOOL_FUNCTIONS.get(name)
            if fn:
                self._tools[name] = {
                    "name": name,
                    "description": td["description"],
                    "tool_type": td["tool_type"],
                    "input_schema": td["input_schema"],
                    "function": fn,
                }

    def get_tool(self, name: str) -> dict | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "tool_type": t["tool_type"],
                "input_schema": t["input_schema"],
            }
            for t in self._tools.values()
        ]

    @property
    def tool_count(self) -> int:
        return len(self._tools)


_registry = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _registry.load_from_definitions()
    return _registry
