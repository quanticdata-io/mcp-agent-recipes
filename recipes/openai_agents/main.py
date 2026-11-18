"""OpenAI Agents SDK: answer a question from the web and cite the sources.

The agent gets two QuanticData MCP tools, ``search`` and ``scrape``, through
``agents.mcp.MCPServerStreamableHttp`` (or ``MCPServerStdio`` with ``--transport local``)
and a static tool filter.

    uv run python -m recipes.openai_agents.main "What changed in the latest HTTP/3 RFC?"

Needs QUANTICDATA_API_KEY and OPENAI_API_KEY.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from agents import Agent, Runner
from agents.mcp import MCPServer, MCPServerStdio, MCPServerStreamableHttp, create_static_tool_filter

from qd_mcp_config import SERVER_NAME, QuanticDataMCP
from recipes._cli import base_parser, run_main

TOOLS = ("search", "scrape")

INSTRUCTIONS = """You answer questions from the live web.
1. Call `search` once or twice to find candidate sources.
2. Call `scrape` on the two or three most relevant result URLs (format markdown) to read them.
3. Answer in a few short paragraphs, using only what the pages say.
4. End with a "Sources" list of the URLs you read. If the pages do not answer the question, say so."""


def build_server(config: QuanticDataMCP) -> MCPServerStreamableHttp | MCPServerStdio:
    """The QuanticData MCP server, restricted to ``TOOLS``. Nothing connects until ``async with``."""
    tool_filter = create_static_tool_filter(allowed_tool_names=list(TOOLS))
    if config.transport == "remote":
        return MCPServerStreamableHttp(
            params=config.openai_agents_params(),  # type: ignore[arg-type]
            name=SERVER_NAME,
            cache_tools_list=True,
            client_session_timeout_seconds=120,
            tool_filter=tool_filter,
        )
    return MCPServerStdio(
        params=config.openai_agents_params(),  # type: ignore[arg-type]
        name=SERVER_NAME,
        cache_tools_list=True,
        client_session_timeout_seconds=120,
        tool_filter=tool_filter,
    )


def build_agent(server: MCPServer, model: str | None = None) -> Agent[None]:
    """``model=None`` uses the Agents SDK's default model."""
    return Agent(name="Web researcher", instructions=INSTRUCTIONS, mcp_servers=[server], model=model)


async def research(
    question: str, *, model: str | None = None, transport: str | None = None, max_turns: int = 10
) -> str:
    config = QuanticDataMCP.from_env(transport=transport)
    async with build_server(config) as server:
        result = await Runner.run(build_agent(server, model), question, max_turns=max_turns)
    return str(result.final_output)


def parser() -> argparse.ArgumentParser:
    p = base_parser("Answer a question from the web with the QuanticData MCP server (OpenAI Agents SDK).")
    p.add_argument("question", help="The question to research")
    p.add_argument("--model", default=None, help="OpenAI model name (default: the Agents SDK default)")
    return p


async def _run(args: argparse.Namespace) -> str:
    return await research(args.question, model=args.model, transport=args.transport, max_turns=args.max_turns)


def main(argv: Sequence[str] | None = None) -> int:
    return run_main(parser(), argv, _run)


if __name__ == "__main__":
    raise SystemExit(main())
