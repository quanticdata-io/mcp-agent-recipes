# Contributing

Recipes for more frameworks and better tasks are welcome.

## Setup

```bash
git clone https://github.com/quanticdata-io/mcp-agent-recipes
cd mcp-agent-recipes
uv sync                     # Python 3.11 or later
```

## Checks

CI runs these on Python 3.11 to 3.13, on Ubuntu and Windows:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

The optional live test lists the tools of the real server (no tool is called, no model is used):

```bash
QD_LIVE_TESTS=1 QUANTICDATA_API_KEY=qd_live_... uv run pytest -m live
```

## Ground rules

- One recipe per framework, in `recipes/<name>/main.py`, with a CLI (`--transport`, `--model`, `--max-turns`) and an async function that the tests can call.
- Attach the MCP server the way the framework documents it (its own MCP client class or option). Build the configuration with `qd_mcp_config.QuanticDataMCP`, never read the key directly.
- Allow only the tools the task needs (`TOOLS` in each recipe). Every tool call is billed to the user's account.
- Tests never call the QuanticData API, a model provider or a website: replace the SDK entry point (`Runner.run`, `query`, `MultiServerMCPClient`, `create_agent`) with a fake, and check what the recipe passes to it.
- The key must not appear in output, logs or exceptions. `tests/test_config.py` checks the configuration object; keep that true for new code.
- Examples target public sample sites (`books.toscrape.com`, `quotes.toscrape.com`, `example.com`) or general questions, and collect no personal data.

## Why the recipes differ

Each framework has its own way to attach an MCP server and to restrict tools:

| Framework | Attach | Restrict tools |
| --- | --- | --- |
| OpenAI Agents SDK | `MCPServerStreamableHttp` / `MCPServerStdio` in `Agent(mcp_servers=...)` | `create_static_tool_filter(allowed_tool_names=...)` |
| Claude Agent SDK | `ClaudeAgentOptions(mcp_servers={...})` | `allowed_tools=["mcp__quanticdata__<tool>"]`, `tools=[]`, `permission_mode="dontAsk"` |
| LangGraph | `MultiServerMCPClient({...}).get_tools()` | filter the returned tools by name before `create_agent` |
