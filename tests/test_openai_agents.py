from __future__ import annotations

from types import SimpleNamespace, TracebackType
from typing import Any

import agents
import pytest
from agents.mcp import MCPServerStdio, MCPServerStreamableHttp

from qd_mcp_config import QuanticDataMCP
from recipes.openai_agents import main as recipe
from tests.conftest import FAKE_KEY


def test_remote_server_is_built_without_connecting(api_key: str) -> None:
    server = recipe.build_server(QuanticDataMCP.from_env())
    assert isinstance(server, MCPServerStreamableHttp)
    assert server.name == "quanticdata"
    assert server.params["url"] == "https://api.quanticdata.io/mcp"
    assert server.params["headers"] == {"Authorization": f"Bearer {api_key}"}
    assert server.tool_filter == {"allowed_tool_names": ["search", "scrape"]}


def test_local_server_uses_stdio(api_key: str) -> None:
    server = recipe.build_server(QuanticDataMCP.from_env(transport="local"))
    assert isinstance(server, MCPServerStdio)
    assert server.tool_filter == {"allowed_tool_names": ["search", "scrape"]}


def test_agent_wires_the_server(api_key: str) -> None:
    server = recipe.build_server(QuanticDataMCP.from_env())
    agent = recipe.build_agent(server, model="some-model")
    assert agent.mcp_servers == [server]
    assert agent.model == "some-model"
    assert "Sources" in str(agent.instructions)


class FakeServer:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> FakeServer:
        self.entered = True
        return self

    async def __aexit__(self, *exc: type[BaseException] | BaseException | TracebackType | None) -> None:
        self.exited = True


async def test_research_runs_the_agent_inside_the_server_context(
    api_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeServer()
    seen: dict[str, Any] = {}

    async def fake_run(agent: Any, question: str, *, max_turns: int) -> Any:
        assert fake.entered
        assert not fake.exited
        seen.update(agent=agent, question=question, max_turns=max_turns)
        return SimpleNamespace(final_output="Answer.\n\nSources\n- https://example.com/")

    monkeypatch.setattr(recipe, "build_server", lambda cfg: fake)
    monkeypatch.setattr(agents.Runner, "run", fake_run)
    answer = await recipe.research("What is example.com?", max_turns=4)
    assert answer.startswith("Answer.")
    assert fake.exited
    assert seen["question"] == "What is example.com?"
    assert seen["max_turns"] == 4
    assert seen["agent"].mcp_servers == [fake]


def test_cli_prints_the_answer(
    api_key: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_research(question: str, **kwargs: Any) -> str:
        assert kwargs == {"model": "m", "transport": "local", "max_turns": 3}
        return f"answer to {question}"

    monkeypatch.setattr(recipe, "research", fake_research)
    assert recipe.main(["q?", "--model", "m", "--transport", "local", "--max-turns", "3"]) == 0
    assert capsys.readouterr().out.strip() == "answer to q?"


def test_cli_without_key_exits_2(no_key: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert recipe.main(["q?"]) == 2
    err = capsys.readouterr().err
    assert "QUANTICDATA_API_KEY is not set" in err
    assert FAKE_KEY not in err
