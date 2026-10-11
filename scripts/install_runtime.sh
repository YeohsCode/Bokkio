#!/bin/sh
set -eu
project_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$(uname -s)" != Darwin ]; then
    echo 'This installer targets macOS.' >&2
    exit 1
fi
command -v uv >/dev/null 2>&1 || { echo 'Install uv from its official distribution, then rerun.' >&2; exit 1; }
command -v xcrun >/dev/null 2>&1 || { echo 'Apple Command Line Tools are required for native helpers.' >&2; exit 1; }
cd "$project_dir"
uv sync --frozen --extra mcp --extra browser
uv run python -c 'import sys; assert sys.version_info >= (3, 10), "MCP requires Python 3.10+"'
uv run python -m playwright install chromium
uv run bokkio-runtime --help
echo 'Grant Accessibility and Screen Recording to the resolved Python/host using macOS system settings.'
echo 'Review examples/runtime-policy.json and use docs/RUNTIME-GUIDE.md to start the runtime.'
