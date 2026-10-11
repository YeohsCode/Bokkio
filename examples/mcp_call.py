"""One MCP tool call through the official client; reusable by an Agent shell tool.

A fresh stdio connection is safe: sessions, jobs, observations and browser workers
live in the shared Runtime state. This client never grants approvals.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys


async def call(args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    command = ["-m", "bokkio.runtime_cli", "--state", str(args.state.resolve()),
               "--policy", str(args.policy.resolve()), "serve"]
    parameters = StdioServerParameters(command=sys.executable, args=command)
    request = {"arguments": json.loads(args.args_file.read_text(encoding="utf-8") if args.args_file else args.arguments)}
    if args.session:
        request["session_id"] = args.session
    if args.operation:
        request["operation_id"] = args.operation
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize()
            result = await client.call_tool(args.tool, request)
            structured = result.structuredContent
            if args.output:
                args.output.write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(structured, ensure_ascii=False))
            return 1 if result.isError else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--session")
    parser.add_argument("--operation")
    parser.add_argument("--arguments", default="{}")
    parser.add_argument("--args-file", type=Path)
    parser.add_argument("--output", type=Path)
    raise SystemExit(asyncio.run(call(parser.parse_args())))
