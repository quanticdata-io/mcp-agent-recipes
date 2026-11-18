"""Optional checks against the real QuanticData MCP server.

Skipped unless QD_LIVE_TESTS=1 and QUANTICDATA_API_KEY are set. They only list the
server's tools (no scrape, no search, no model call), to confirm that every tool a
recipe allows is offered by the server.

    QD_LIVE_TESTS=1 QUANTICDATA_API_KEY=qd_live_... pytest -m live
"""

from __future__ import annotations

import os

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from qd_mcp_config import QuanticDataMCP
from recipes.claude_agent import main as claude_recipe
from recipes.langgraph_agent import main as langgraph_recipe
from recipes.openai_agents import main as openai_recipe

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("QD_LIVE_TESTS") != "1" or not os.environ.get("QUANTICDATA_API_KEY"),
        reason="set QD_LIVE_TESTS=1 and QUANTICDATA_API_KEY to run",
    ),
]


async def test_hosted_server_offers_every_recipe_tool() -> None:
    cfg = QuanticDataMCP.from_env(transport="remote")
    async with (
        streamablehttp_client(cfg.url, headers=cfg.headers()) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        names = {t.name for t in (await session.list_tools()).tools}
    for recipe_tools in (openai_recipe.TOOLS, claude_recipe.TOOLS, langgraph_recipe.TOOLS):
        assert set(recipe_tools) <= names
