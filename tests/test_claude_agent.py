from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock

from qd_mcp_config import QuanticDataMCP
from recipes.claude_agent import main as recipe
from tests.conftest import FAKE_KEY


def result(**overrides: Any) -> ResultMessage:
    fields: dict[str, Any] = {
        "subtype": "success",
        "duration_ms": 10,
        "duration_api_ms": 8,
        "is_error": False,
        "num_turns": 3,
        "session_id": "session-example",
        "result": "| Section | URLs |\n| --- | --- |\n| /catalogue/category | 51 |",
    }
    fields.update(overrides)
    return ResultMessage(**fields)


def test_options_attach_only_the_quanticdata_server(api_key: str) -> None:
    opts = recipe.build_options(QuanticDataMCP.from_env(), max_turns=6)
    assert isinstance(opts, ClaudeAgentOptions)
    assert opts.mcp_servers == {
        "quanticdata": {
            "type": "http",
            "url": "https://api.quanticdata.io/mcp",
            "headers": {"Authorization": f"Bearer {api_key}"},
        }
    }
    assert opts.strict_mcp_config is True
    assert opts.tools == []
    assert opts.allowed_tools == ["mcp__quanticdata__map", "mcp__quanticdata__scrape"]
    assert opts.permission_mode == "dontAsk"
    assert opts.model == "claude-opus-5-5"
    assert opts.max_turns == 6


def test_options_local_transport(api_key: str) -> None:
    opts = recipe.build_options(QuanticDataMCP.from_env(transport="local"))
    assert isinstance(opts.mcp_servers, dict)
    server = opts.mcp_servers["quanticdata"]
    assert server["type"] == "stdio"
    assert server["args"] == ["-y", "quanticdata-mcp"]


async def test_returns_the_result_message(api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    async def fake_query(*, prompt: str, options: ClaudeAgentOptions) -> AsyncIterator[Any]:
        seen.update(prompt=prompt, options=options)
        yield AssistantMessage(content=[TextBlock(text="Mapping the site.")], model="claude-opus-5-5")
        yield result()

    monkeypatch.setattr(recipe, "query", fake_query)
    text = await recipe.summarise_site("https://books.toscrape.com/", model="claude-opus-5-5")
    assert "/catalogue/category" in text
    assert seen["prompt"] == "Map https://books.toscrape.com/ and summarise its sections."


async def test_error_result_raises(api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_query(*, prompt: str, options: ClaudeAgentOptions) -> AsyncIterator[Any]:
        yield result(is_error=True, subtype="error_max_turns", result=None, errors=["max turns"])

    monkeypatch.setattr(recipe, "query", fake_query)
    with pytest.raises(recipe.AgentRunError, match="error_max_turns"):
        await recipe.summarise_site("https://books.toscrape.com/")


async def test_no_result_raises(api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_query(*, prompt: str, options: ClaudeAgentOptions) -> AsyncIterator[Any]:
        if False:  # pragma: no cover - makes this an async generator
            yield None

    monkeypatch.setattr(recipe, "query", fake_query)
    with pytest.raises(recipe.AgentRunError, match="without a result"):
        await recipe.summarise_site("https://books.toscrape.com/")


def test_cli_default_url_and_missing_key(no_key: None, capsys: pytest.CaptureFixture[str]) -> None:
    args = recipe.parser().parse_args([])
    assert args.url == "https://books.toscrape.com/"
    assert recipe.main([]) == 2
    assert FAKE_KEY not in capsys.readouterr().err
