# MCP agent recipes

Runnable Python recipes that give an AI agent live web data through the [QuanticData MCP server](https://quanticdata.io/mcp-server/), one per agent framework: the OpenAI Agents SDK, the Claude Agent SDK and LangGraph. Each recipe does a real task, attaches the server the way its framework documents, and allows only the tools the task needs.

[![CI](https://github.com/quanticdata-io/mcp-agent-recipes/actions/workflows/ci.yml/badge.svg)](https://github.com/quanticdata-io/mcp-agent-recipes/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

| Recipe | Framework | Task | QuanticData tools | Model key |
| --- | --- | --- | --- | --- |
| [`recipes/openai_agents`](recipes/openai_agents/main.py) | [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) | Answer a question from the web and list the sources it read | `search`, `scrape` | `OPENAI_API_KEY` |
| [`recipes/claude_agent`](recipes/claude_agent/main.py) | [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) | Map a site and summarise its sections in a table | `map`, `scrape` | `ANTHROPIC_API_KEY` |
| [`recipes/langgraph_agent`](recipes/langgraph_agent/main.py) | [LangGraph](https://langchain-ai.github.io/langgraph/) via [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) | Compare the prices on a shop category page | `scrape` | `ANTHROPIC_API_KEY` (default model) |

## Install

From source (the recipes are not published as a package):

```bash
git clone https://github.com/quanticdata-io/mcp-agent-recipes
cd mcp-agent-recipes
uv sync            # Python 3.11 or later; installs the versions pinned in uv.lock
```

Set the keys:

```bash
export QUANTICDATA_API_KEY=qd_live_your_key     # API keys page of the QuanticData dashboard
export OPENAI_API_KEY=...                       # for the OpenAI Agents SDK recipe
export ANTHROPIC_API_KEY=...                    # for the Claude Agent SDK and LangGraph recipes
```

## Run

```bash
uv run python -m recipes.openai_agents.main "What does the robots.txt standard say about crawl delays?"
uv run python -m recipes.claude_agent.main https://books.toscrape.com/
uv run python -m recipes.langgraph_agent.main https://books.toscrape.com/catalogue/category/books/poetry_23/index.html
```

Each command prints the agent's final answer. A missing `QUANTICDATA_API_KEY` exits with code 2 and a message that says what to set.

### What the tools return

The agents work from the tool results of the MCP server. Two calls made on 2026-11-18, trimmed:

`map` on `https://books.toscrape.com/` with `group_by: "path"` (what the Claude Agent SDK recipe starts from):

```json
{
  "url": "https://books.toscrape.com/",
  "total": 73,
  "summary": { "/catalogue": 72, "/index.html": 1 },
  "groups": { "/catalogue/category": 51, "/index.html": 1, "/catalogue/a-light-in-the-attic_1000": 1, "/catalogue/page-2.html": 1 },
  "sources": { "sitemap": 0, "homepage": 73 }
}
```

`scrape` on the poetry category with the `extract` schema of the LangGraph recipe:

```json
{
  "url": "https://books.toscrape.com/catalogue/category/books/poetry_23/index.html",
  "status": 200,
  "title": "Poetry | Books to Scrape - Sandbox",
  "data": {
    "titles": ["A Light in the Attic", "The Black Maria", "Shakespeare's Sonnets", "..."],
    "prices": ["£51.77", "£52.15", "£20.66", "..."],
    "stock": ["In stock", "In stock", "In stock", "..."]
  }
}
```

## Options

Every recipe takes:

| Option | Meaning |
| --- | --- |
| `--transport remote\|local` | `remote` (default): the hosted endpoint over Streamable HTTP. `local`: starts `npx -y quanticdata-mcp` as a stdio subprocess (needs Node.js). Overrides `QUANTICDATA_MCP_TRANSPORT` |
| `--model` | Model for the agent. OpenAI Agents SDK: an OpenAI model name, default: the SDK's default model. Claude Agent SDK: a Claude model id, default `claude-opus-5-5`. LangGraph: `provider:model` for LangChain's `init_chat_model`, default `anthropic:claude-opus-5-5` (another provider needs its LangChain package, e.g. `langchain-openai`) |
| `--max-turns` | Limit on agent turns (default 10). LangGraph maps it to a recursion limit of `2 * max_turns + 1` |

Positional arguments: the question (`openai_agents`, required), the site URL (`claude_agent`, default `https://books.toscrape.com/`), the category page (`langgraph_agent`, default the poetry category of `books.toscrape.com`).

Environment variables, read by [`qd_mcp_config.py`](qd_mcp_config.py):

| Variable | Meaning |
| --- | --- |
| `QUANTICDATA_API_KEY` | Required. Sent as `Authorization: Bearer <key>` to the hosted endpoint, or passed to the local server's environment |
| `QUANTICDATA_MCP_URL` | Hosted endpoint, default `https://api.quanticdata.io/mcp`. The server documents `?tools=web` and `?tools=lite` to load a smaller tool set; the recipes already filter tools on the client |
| `QUANTICDATA_MCP_TRANSPORT` | `remote` (default) or `local` |
| `QD_LIVE_TESTS` | `1` runs the optional live test (see below) |

## Use the configuration in your own agent

```python
from qd_mcp_config import QuanticDataMCP, claude_tool_names

cfg = QuanticDataMCP.from_env()  # raises MissingApiKeyError with a clear message
cfg.openai_agents_params()  # params for agents.mcp.MCPServerStreamableHttp / MCPServerStdio
cfg.claude_agent_server()  # one entry of ClaudeAgentOptions.mcp_servers
cfg.langchain_connection()  # one connection of MultiServerMCPClient
claude_tool_names(["search", "scrape"])  # ["mcp__quanticdata__search", "mcp__quanticdata__scrape"]
print(cfg)  # QuanticDataMCP(api_key='qd_live_****', url=..., transport='remote')
```

## The MCP server

- Hosted: `https://api.quanticdata.io/mcp`, Streamable HTTP. The server accepts the key in the `Authorization: Bearer` or `X-Api-Key` header, or OAuth sign-in in clients that support MCP authorization. The recipes use the Bearer header.
- Local: `npx -y quanticdata-mcp` with `QUANTICDATA_API_KEY` in its environment.
- Both offered the same 29 tools when checked on 2026-11-18 (hosted endpoint and npm package 0.11.12). The recipes use `search`, `scrape` and `map`; the others include `crawl`, `batch`, `search_and_read`, `run_collector` and `seo_audit`. Details on [quanticdata.io/mcp-server](https://quanticdata.io/mcp-server/) and the [API reference](https://quanticdata.io/docs/).

## Cost

Every tool call the agent makes is billed to your QuanticData account like the matching API call, and the model calls are billed by the model provider. See [pricing](https://quanticdata.io/pricing/). The recipes keep costs bounded with a small tool allow-list, prompts that cap the pages read (two or three in the research recipe, five in the site summary, one in the price comparison) and `--max-turns`.

## Tests

```bash
uv run pytest            # offline: no QuanticData, model provider or website calls
```

- `tests/test_config.py`: configuration from the environment, URL and transport overrides, the per-framework shapes, the local command, key masking in `repr()`, `str()` and logs, and that the local subprocess does not inherit other secrets.
- `tests/test_openai_agents.py`, `tests/test_claude_agent.py`, `tests/test_langgraph_agent.py`: each recipe builds its server, options or client offline, restricts the tools, and passes the right arguments to the framework; the framework entry points (`Runner.run`, `query`, `MultiServerMCPClient`, `create_agent`) are replaced by fakes.
- `tests/test_live.py` (skipped by default): connects to the real hosted server and checks that every tool a recipe allows is in its tool list. It calls no tool and no model:

  ```bash
  QD_LIVE_TESTS=1 QUANTICDATA_API_KEY=qd_live_your_key uv run pytest -m live
  ```

To run a recipe end to end against the real API, set the keys above and use the commands in [Run](#run).

## Limits

- The answers come from a model: they can be incomplete or wrong. The prompts ask the agents to use only what the tools returned and to list sources; check them.
- The tests check the wiring, not the agents' answers. The live test checks the tool list only.
- The SDKs move fast. The recipes were written against openai-agents 0.25, claude-agent-sdk 0.2.184, langchain 1.5, langgraph 1.2 and langchain-mcp-adapters 0.3 (pinned in `uv.lock`).
- The LangGraph recipe's `extract` selectors fit `books.toscrape.com`; for another shop, change them in the system prompt.
- The Claude Agent SDK runs the Claude Code runtime that ships with the package. Built-in tools are switched off in the recipe, so the agent cannot read or write local files or run commands.

## Responsible use

- Read public pages only, at a modest rate, and respect each site's terms and `robots.txt`. The defaults point at sites built for scraping practice.
- Do not point the agents at personal data. Tool results go to the model provider you use.

## License

[MIT](LICENSE)
