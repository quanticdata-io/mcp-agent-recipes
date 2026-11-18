"""Claude Agent SDK: map a site and summarise its sections.

The agent gets the QuanticData MCP server through ``ClaudeAgentOptions.mcp_servers``.
Only ``map`` and ``scrape`` are pre-approved; built-in tools (Bash, file editing, web
fetch) are switched off and every other tool call is refused (``permission_mode="dontAsk"``).

    uv run python -m recipes.claude_agent.main https://books.toscrape.com/

Needs QUANTICDATA_API_KEY and ANTHROPIC_API_KEY (or a Claude login the SDK can use).
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator, Sequence
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from qd_mcp_config import SERVER_NAME, QuanticDataMCP, claude_tool_names
from recipes._cli import base_parser, run_main

TOOLS = ("map", "scrape")
DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You describe the structure of a website.
1. Call the `map` tool once on the URL with group_by "path" to get the site's sections and their URL counts.
2. Call `scrape` (format markdown, max_tokens 2000) on the home page and on one representative page of each of
   the largest sections, at most five pages in total.
3. Reply in Markdown: one line on what the site is, then a table with section path, URL count and a
   one-sentence summary of what the section contains. Base every summary on a page you read; mark the
   sections you did not read."""


class AgentRunError(RuntimeError):
    """The agent run ended with an error result."""


def build_options(
    config: QuanticDataMCP, *, model: str = DEFAULT_MODEL, max_turns: int = 10
) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        mcp_servers={SERVER_NAME: config.claude_agent_server()},  # type: ignore[dict-item]
        strict_mcp_config=True,
        tools=[],
        allowed_tools=claude_tool_names(TOOLS),
        permission_mode="dontAsk",
        system_prompt=SYSTEM_PROMPT,
        model=model,
        max_turns=max_turns,
    )


def prompt_for(url: str) -> str:
    return f"Map {url} and summarise its sections."


async def summarise_site(
    url: str, *, model: str = DEFAULT_MODEL, transport: str | None = None, max_turns: int = 10
) -> str:
    config = QuanticDataMCP.from_env(transport=transport)
    messages: AsyncIterator[Any] = query(
        prompt=prompt_for(url), options=build_options(config, model=model, max_turns=max_turns)
    )
    async for message in messages:
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise AgentRunError(
                    f"Agent run failed ({message.subtype}): {message.result or message.errors}"
                )
            return message.result or ""
    raise AgentRunError("The agent ended without a result message")


def parser() -> argparse.ArgumentParser:
    p = base_parser(
        "Map a site and summarise its sections with the QuanticData MCP server (Claude Agent SDK)."
    )
    p.add_argument("url", nargs="?", default="https://books.toscrape.com/", help="Site to map")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model id (default {DEFAULT_MODEL})")
    return p


async def _run(args: argparse.Namespace) -> str:
    return await summarise_site(
        args.url, model=args.model, transport=args.transport, max_turns=args.max_turns
    )


def main(argv: Sequence[str] | None = None) -> int:
    return run_main(parser(), argv, _run)


if __name__ == "__main__":
    raise SystemExit(main())
