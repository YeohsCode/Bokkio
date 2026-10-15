"""Official MCP SDK transport; no model, planning loop or approval-granting tool."""
from __future__ import annotations

import asyncio
import json

from .runtime import TOOLS, READ_TOOLS
from .tool_schema import SCHEMAS, DESCRIPTIONS


async def serve(runtime):
    exposed_tools = getattr(runtime, "tools", TOOLS)
    schemas = {**SCHEMAS, **getattr(runtime, "schemas", {})}
    descriptions = {**DESCRIPTIONS, **getattr(runtime, "descriptions", {})}
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types

    server = Server("bokkio")

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=tool, description=descriptions.get(tool, "Bokkio " + tool + "; resource scope is granted by the host policy.")
                           + " Put business fields inside arguments. session_id and operation_id are sibling envelope fields; use the session_id returned by session.open.",
                           inputSchema={"type": "object", "properties": {
                               "arguments": schemas[tool], "session_id": {"type": "string"}, "operation_id": {"type": "string"}},
                               "required": ([] if tool in {"capabilities", "session.open"} else ["session_id"])
                                   + (["arguments"] if schemas[tool]["required"] else []),
                               "additionalProperties": False},
                           annotations=types.ToolAnnotations(readOnlyHint=tool in READ_TOOLS and tool != "job.get",
                                                             destructiveHint=tool not in READ_TOOLS or tool == "job.get")) for tool in sorted(exposed_tools)]

    @server.call_tool()
    async def call_tool(name, arguments):
        arguments = arguments or {}
        result = await asyncio.to_thread(runtime.call, name, arguments.get("arguments", {}),
                                        session_id=arguments.get("session_id"), operation_id=arguments.get("operation_id"))
        content = [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        structured = result
        if name == "artifact.read" and result.get("status") == "completed" and result["result"].get("mime", "").startswith("image/"):
            structured = {**result, "result": {k: v for k, v in result["result"].items() if k != "data_base64"}}
            content = [types.ImageContent(type="image", data=result["result"]["data_base64"], mimeType=result["result"]["mime"]),
                       types.TextContent(type="text", text=json.dumps(structured))]
        return types.CallToolResult(content=content, structuredContent=structured,
                                    isError=result.get("status") in {"failed", "denied", "completion_unknown"})

    async with stdio_server() as streams:
        await server.run(*streams, server.create_initialization_options())
