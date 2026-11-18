"""LangGraph: compare book prices on a public sample shop.

Loads the QuanticData MCP tools with ``langchain_mcp_adapters.client.MultiServerMCPClient``,
keeps only ``scrape``, and runs them in LangChain's prebuilt tool-calling agent
(``langchain.agents.create_agent``, a LangGraph graph).

    uv run python -m recipes.langgraph_agent.main https://books.toscrape.com/catalogue/category/books/poetry_23/index.html

Needs QUANTICDATA_API_KEY and the key of the chat model provider (ANTHROPIC_API_KEY for the default model).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from qd_mcp_config import SERVER_NAME, QuanticDataMCP
from recipes._cli import base_parser, run_main

TOOLS = ("scrape",)
DEFAULT_MODEL = "anthropic:claude-opus-5-5"
DEFAULT_URL = "https://books.toscrape.com/catalogue/category/books/poetry_23/index.html"

SYSTEM_PROMPT = """You compare product prices on a shop category page.
Call `scrape` once on the URL with format "text", max_tokens 500 and this `extract` schema, which reads every
product card of a books.toscrape.com category page (adapt the selectors for another shop):
{"titles": {"selector": "article.product_pod h3 a", "attr": "title", "all": true},
 "prices": {"selector": "article.product_pod .price_color", "all": true},
 "stock": {"selector": "article.product_pod .availability", "all": true}}.
Then answer with a Markdown table of the five cheapest products (title, price, availability), the price range,
and the number of products on the page. Use only values the tool returned."""


class EmptyToolsetError(RuntimeError):
    """The MCP server did not offer the tools this recipe needs."""


def select_tools(tools: Sequence[BaseTool], allowed: Sequence[str] = TOOLS) -> list[BaseTool]:
    chosen = [t for t in tools if t.name in allowed]
    missing = set(allowed) - {t.name for t in chosen}
    if missing:
        raise EmptyToolsetError(f"The MCP server did not list: {', '.join(sorted(missing))}")
    return chosen


def build_client(config: QuanticDataMCP) -> MultiServerMCPClient:
    return MultiServerMCPClient({SERVER_NAME: config.langchain_connection()})  # type: ignore[dict-item]


def final_text(state: dict[str, Any]) -> str:
    """Text of the last message of an agent run (content may be a string or a list of blocks)."""
    content = state["messages"][-1].content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


async def compare_prices(
    url: str = DEFAULT_URL, *, model: str = DEFAULT_MODEL, transport: str | None = None, max_turns: int = 10
) -> str:
    config = QuanticDataMCP.from_env(transport=transport)
    tools = select_tools(await build_client(config).get_tools(server_name=SERVER_NAME))
    agent = create_agent(model, tools, system_prompt=SYSTEM_PROMPT)
    state = await agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Compare the prices on {url}"}]},
        config={"recursion_limit": 2 * max_turns + 1},
    )
    return final_text(state)


def parser() -> argparse.ArgumentParser:
    p = base_parser("Compare product prices on a category page with the QuanticData MCP server (LangGraph).")
    p.add_argument("url", nargs="?", default=DEFAULT_URL, help="Category page to read")
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Chat model as provider:model for init_chat_model (default {DEFAULT_MODEL})",
    )
    return p


async def _run(args: argparse.Namespace) -> str:
    return await compare_prices(
        args.url, model=args.model, transport=args.transport, max_turns=args.max_turns
    )


def main(argv: Sequence[str] | None = None) -> int:
    return run_main(parser(), argv, _run)


if __name__ == "__main__":
    raise SystemExit(main())
