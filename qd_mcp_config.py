"""Shared QuanticData MCP server configuration for every recipe.

Reads the environment once and produces the server configuration each framework
expects. The API key is kept out of ``repr()`` and ``str()`` so it does not end up
in logs or tracebacks by accident.

Environment variables:

``QUANTICDATA_API_KEY``
    Required. Created on the API keys page of the QuanticData dashboard.
``QUANTICDATA_MCP_URL``
    Optional. Hosted endpoint, default ``https://api.quanticdata.io/mcp``.
``QUANTICDATA_MCP_TRANSPORT``
    Optional. ``remote`` (default, Streamable HTTP to the hosted endpoint) or
    ``local`` (runs ``npx -y quanticdata-mcp`` as a stdio subprocess).
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from mcp.client.stdio import get_default_environment

DEFAULT_URL = "https://api.quanticdata.io/mcp"
SERVER_NAME = "quanticdata"
NPM_PACKAGE = "quanticdata-mcp"

Transport = Literal["remote", "local"]
TRANSPORTS: tuple[Transport, ...] = ("remote", "local")


class ConfigError(RuntimeError):
    """The environment does not describe a usable MCP server configuration."""


class MissingApiKeyError(ConfigError):
    def __init__(self) -> None:
        super().__init__(
            "QUANTICDATA_API_KEY is not set. Create a key on the API keys page of the "
            "QuanticData dashboard and export it, e.g. export QUANTICDATA_API_KEY=qd_live_..."
        )


def mask(secret: str) -> str:
    """Shows the key's prefix only, e.g. ``qd_live_****``."""
    head, sep, _ = secret.partition("_live_")
    return f"{head}{sep}****" if sep else "****"


@dataclass(frozen=True)
class QuanticDataMCP:
    api_key: str = field(repr=False)
    url: str = DEFAULT_URL
    transport: Transport = "remote"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise MissingApiKeyError
        if self.transport not in TRANSPORTS:
            raise ConfigError(f"QUANTICDATA_MCP_TRANSPORT must be one of {', '.join(TRANSPORTS)}")
        if not self.url.startswith(("https://", "http://")):
            raise ConfigError("QUANTICDATA_MCP_URL must be an http(s) URL")

    def __repr__(self) -> str:
        return (
            f"QuanticDataMCP(api_key={mask(self.api_key)!r}, url={self.url!r}, transport={self.transport!r})"
        )

    __str__ = __repr__

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None, *, transport: str | None = None
    ) -> QuanticDataMCP:
        """Builds the configuration from ``env`` (default: ``os.environ``).

        ``transport`` overrides ``QUANTICDATA_MCP_TRANSPORT`` (the recipes pass their
        ``--transport`` flag here).
        """
        env = os.environ if env is None else env
        key = env.get("QUANTICDATA_API_KEY", "").strip()
        if not key:
            raise MissingApiKeyError
        chosen = (transport or env.get("QUANTICDATA_MCP_TRANSPORT") or "remote").strip().lower()
        if chosen not in TRANSPORTS:
            raise ConfigError(f"Transport must be one of {', '.join(TRANSPORTS)}, got {chosen!r}")
        url = env.get("QUANTICDATA_MCP_URL", "").strip() or DEFAULT_URL
        return cls(api_key=key, url=url, transport=chosen)  # type: ignore[arg-type,unused-ignore]

    # -- building blocks ---------------------------------------------------------------------------

    def headers(self) -> dict[str, str]:
        """Headers for the hosted endpoint: the key as a Bearer token."""
        return {"Authorization": f"Bearer {self.api_key}"}

    def npx_command(self) -> tuple[str, list[str]]:
        """Command for the local stdio server. Resolves ``npx.cmd`` on Windows."""
        return shutil.which("npx") or "npx", ["-y", NPM_PACKAGE]

    def subprocess_env(self) -> dict[str, str]:
        """Environment for the local server: the MCP SDK's safe defaults plus the key."""
        return {**get_default_environment(), "QUANTICDATA_API_KEY": self.api_key}

    # -- per framework -----------------------------------------------------------------------------

    def openai_agents_params(self) -> dict[str, Any]:
        """``params`` for ``agents.mcp.MCPServerStreamableHttp`` or ``MCPServerStdio``."""
        if self.transport == "remote":
            return {"url": self.url, "headers": self.headers(), "timeout": 30, "sse_read_timeout": 300}
        command, args = self.npx_command()
        return {"command": command, "args": args, "env": self.subprocess_env()}

    def claude_agent_server(self) -> dict[str, Any]:
        """One entry of ``ClaudeAgentOptions.mcp_servers``."""
        if self.transport == "remote":
            return {"type": "http", "url": self.url, "headers": self.headers()}
        command, args = self.npx_command()
        return {"type": "stdio", "command": command, "args": args, "env": self.subprocess_env()}

    def langchain_connection(self) -> dict[str, Any]:
        """One connection of ``langchain_mcp_adapters.client.MultiServerMCPClient``."""
        if self.transport == "remote":
            return {"transport": "streamable_http", "url": self.url, "headers": self.headers()}
        command, args = self.npx_command()
        return {"transport": "stdio", "command": command, "args": args, "env": self.subprocess_env()}


def claude_tool_names(tools: Iterable[str], server: str = SERVER_NAME) -> list[str]:
    """Claude Agent SDK names of MCP tools: ``mcp__<server>__<tool>``."""
    return [f"mcp__{server}__{t}" for t in tools]
