from __future__ import annotations

import logging

import pytest

from qd_mcp_config import (
    DEFAULT_URL,
    SERVER_NAME,
    ConfigError,
    MissingApiKeyError,
    QuanticDataMCP,
    claude_tool_names,
    mask,
)
from tests.conftest import FAKE_KEY


def test_defaults_to_the_hosted_endpoint(api_key: str) -> None:
    cfg = QuanticDataMCP.from_env()
    assert cfg.url == DEFAULT_URL == "https://api.quanticdata.io/mcp"
    assert cfg.transport == "remote"
    assert cfg.headers() == {"Authorization": f"Bearer {api_key}"}


def test_missing_key_explains_what_to_do(no_key: None) -> None:
    with pytest.raises(MissingApiKeyError, match="QUANTICDATA_API_KEY is not set"):
        QuanticDataMCP.from_env()


def test_blank_key_is_missing() -> None:
    with pytest.raises(MissingApiKeyError):
        QuanticDataMCP.from_env({"QUANTICDATA_API_KEY": "   "})
    with pytest.raises(MissingApiKeyError):
        QuanticDataMCP(api_key="")


def test_url_and_transport_overrides() -> None:
    env = {"QUANTICDATA_API_KEY": FAKE_KEY, "QUANTICDATA_MCP_URL": "https://mcp.example.com/mcp?tools=web"}
    assert QuanticDataMCP.from_env(env).url == "https://mcp.example.com/mcp?tools=web"
    assert QuanticDataMCP.from_env({**env, "QUANTICDATA_MCP_TRANSPORT": "LOCAL"}).transport == "local"
    # The --transport flag wins over the environment.
    assert (
        QuanticDataMCP.from_env({**env, "QUANTICDATA_MCP_TRANSPORT": "local"}, transport="remote").transport
        == "remote"
    )


def test_rejects_bad_values() -> None:
    with pytest.raises(ConfigError, match="Transport must be one of"):
        QuanticDataMCP.from_env({"QUANTICDATA_API_KEY": FAKE_KEY}, transport="sse")
    with pytest.raises(ConfigError, match="http"):
        QuanticDataMCP(api_key=FAKE_KEY, url="ftp://example.com")


def test_key_never_appears_in_repr_str_or_logs(caplog: pytest.LogCaptureFixture) -> None:
    cfg = QuanticDataMCP(api_key=FAKE_KEY)
    assert FAKE_KEY not in repr(cfg)
    assert FAKE_KEY not in str(cfg)
    assert "qd_live_****" in repr(cfg)
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("test").info("config: %s %r", cfg, cfg)
    assert FAKE_KEY not in caplog.text


def test_mask() -> None:
    assert mask(FAKE_KEY) == "qd_live_****"
    assert mask("something-else") == "****"


def test_remote_configs_per_framework(api_key: str) -> None:
    cfg = QuanticDataMCP.from_env()
    bearer = {"Authorization": f"Bearer {api_key}"}
    assert cfg.openai_agents_params() == {
        "url": DEFAULT_URL,
        "headers": bearer,
        "timeout": 30,
        "sse_read_timeout": 300,
    }
    assert cfg.claude_agent_server() == {"type": "http", "url": DEFAULT_URL, "headers": bearer}
    assert cfg.langchain_connection() == {
        "transport": "streamable_http",
        "url": DEFAULT_URL,
        "headers": bearer,
    }


def test_local_configs_run_the_npm_package(api_key: str) -> None:
    cfg = QuanticDataMCP.from_env(transport="local")
    command, args = cfg.npx_command()
    assert command.lower().rsplit("/", 1)[-1].rsplit("\\", 1)[-1].startswith("npx")
    assert args == ["-y", "quanticdata-mcp"]
    for built in (cfg.openai_agents_params(), cfg.claude_agent_server(), cfg.langchain_connection()):
        assert built["command"] == command
        assert built["args"] == args
        assert built["env"]["QUANTICDATA_API_KEY"] == api_key
        assert "headers" not in built
        assert "PATH" in built["env"] or "Path" in built["env"]
    assert cfg.claude_agent_server()["type"] == "stdio"
    assert cfg.langchain_connection()["transport"] == "stdio"


def test_subprocess_env_does_not_leak_other_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-not-for-the-mcp-server")
    env = QuanticDataMCP(api_key=FAKE_KEY, transport="local").subprocess_env()
    assert "OPENAI_API_KEY" not in env


def test_claude_tool_names() -> None:
    assert claude_tool_names(["map", "scrape"]) == [f"mcp__{SERVER_NAME}__map", f"mcp__{SERVER_NAME}__scrape"]
