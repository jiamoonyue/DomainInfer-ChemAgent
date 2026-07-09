"""MCP JSON-RPC Server — Design doc 5.4: standardized tool protocol.

Handles tools/list, tools/call, resources/list, resources/read.
Runs in-process (no network overhead), but interface is standard MCP format.
"""

import json

from app.modules.tools.engine import execute_tool, TOOL_DEFINITIONS


class MCPServer:
    """MCP-compatible tool & resource server (in-process).

    Design doc: tools/list -> tools/call -> resources/read.
    """

    def __init__(self, name: str = "agentforge"):
        self.name = name
        self._tools = self._register_tools()

    def _register_tools(self) -> list[dict]:
        tools = []
        for t in TOOL_DEFINITIONS:
            tools.append({
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["input_schema"],
            })
        return tools

    def tools_list(self) -> dict:
        """MCP tools/list."""
        return {
            "jsonrpc": "2.0",
            "result": {"tools": self._tools},
        }

    def tools_call(self, name: str, arguments: dict) -> dict:
        """MCP tools/call."""
        result = execute_tool(name, arguments)
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [{"type": "text", "text": result}],
                "isError": result.startswith("ERROR"),
            },
        }

    def resources_list(self) -> dict:
        """MCP resources/list."""
        return {
            "jsonrpc": "2.0",
            "result": {
                "resources": [
                    {
                        "uri": "chem://knowledge/search",
                        "name": "Knowledge Base Search",
                        "description": "Search chemical engineering knowledge base",
                        "mimeType": "text/plain",
                    },
                    {
                        "uri": "pubchem://compound/{name}",
                        "name": "PubChem Compound Lookup",
                        "description": "Real-time compound data from PubChem (NIH)",
                        "mimeType": "text/plain",
                    },
                ]
            },
        }

    def resources_read(self, uri: str) -> dict:
        """MCP resources/read."""
        from urllib.parse import urlparse
        parsed = urlparse(uri)
        text = ""

        if parsed.scheme == "pubchem" and parsed.netloc == "compound":
            name = parsed.path.strip("/")
            if name:
                from app.modules.tools.engine import pubchem_search
                text = pubchem_search(name)

        return {
            "jsonrpc": "2.0",
            "result": {
                "contents": [{"uri": uri, "mimeType": "text/plain", "text": text}],
            },
        }

    def handle_request(self, method: str, params: dict = None) -> dict:
        """Handle a JSON-RPC request."""
        params = params or {}
        if method == "tools/list":
            return self.tools_list()
        elif method == "tools/call":
            return self.tools_call(params.get("name", ""), params.get("arguments", {}))
        elif method == "resources/list":
            return self.resources_list()
        elif method == "resources/read":
            return self.resources_read(params.get("uri", ""))
        else:
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Unknown method: {method}"}}


_server = None


def get_mcp_server() -> MCPServer:
    global _server
    if _server is None:
        _server = MCPServer()
    return _server
