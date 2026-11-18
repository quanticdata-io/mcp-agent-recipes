from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.tools import BaseTool, tool
from langchain_mcp_adapters.client import MultiServerMCPClient

from qd_mcp_config import QuanticDataMCP
from recipes.langgraph_agent import main as recipe
from tests.conftest import FAKE_KEY


@tool
def scrape(url: str) -> str:
    """Stand-in for the MCP scrape tool."""
    return url


@tool
def crawl(url: str) -> str:
    """Stand-in for the MCP crawl tool."""
    return url


def test_client_gets_the_streamable_http_connection(api_key: str) -> None:
    client = recipe.build_client(QuanticDataMCP.from_env())
    assert isinstance(client, MultiServerMCPClient)
    assert client.connections == {
        "quanticdata": {
            "transport": "streamable_http",
            "url": "https://api.quanticdata.io/mcp",
            "headers": {"Authorization": f"Bearer {api_key}"},
        }
    }


def test_select_tools_keeps_the_allow_list() -> None:
    assert [t.name for t in recipe.select_tools([crawl, scrape])] == ["scrape"]
    with pytest.raises(recipe.EmptyToolsetError, match="scrape"):
        recipe.select_tools([crawl])


def test_final_text_handles_string_and_blocks() -> None:
    assert recipe.final_text({"messages": [SimpleNamespace(content="plain")]}) == "plain"
    blocks = [{"type": "text", "text": "a"}, {"type": "tool_use", "id": "x"}, {"type": "text", "text": "b"}]
    assert recipe.final_text({"messages": [SimpleNamespace(content=blocks)]}) == "ab"


async def test_compare_prices_wires_tools_into_the_agent(
    api_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, connections: dict[str, Any]) -> None:
            seen["connections"] = connections

        async def get_tools(self, *, server_name: str | None = None) -> list[BaseTool]:
            seen["server_name"] = server_name
            return [crawl, scrape]

    class FakeAgent:
        async def ainvoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
            seen.update(state=state, config=config)
            return {"messages": [SimpleNamespace(content="| Title | Price |")]}

    def fake_create_agent(model: str, tools: list[BaseTool], *, system_prompt: str) -> FakeAgent:
        seen.update(model=model, tools=[t.name for t in tools], system_prompt=system_prompt)
        return FakeAgent()

    monkeypatch.setattr(recipe, "MultiServerMCPClient", FakeClient)
    monkeypatch.setattr(recipe, "create_agent", fake_create_agent)
    out = await recipe.compare_prices(max_turns=5)
    assert out == "| Title | Price |"
    assert seen["server_name"] == "quanticdata"
    assert seen["tools"] == ["scrape"]
    assert seen["model"] == "anthropic:claude-opus-5-5"
    assert "article.product_pod" in seen["system_prompt"]
    assert seen["config"] == {"recursion_limit": 11}
    assert recipe.DEFAULT_URL in seen["state"]["messages"][0]["content"]


def test_cli_missing_key(no_key: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert recipe.main([]) == 2
    assert FAKE_KEY not in capsys.readouterr().err
