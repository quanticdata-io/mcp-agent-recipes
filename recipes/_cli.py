"""Command-line plumbing shared by the recipes."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from qd_mcp_config import TRANSPORTS, ConfigError


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default=None,
        help="remote: hosted endpoint over Streamable HTTP (default); local: npx -y quanticdata-mcp. "
        "Overrides QUANTICDATA_MCP_TRANSPORT.",
    )
    parser.add_argument("--max-turns", type=int, default=10, help="Agent turn limit (default 10)")
    return parser


def run_main(
    parser: argparse.ArgumentParser,
    argv: Sequence[str] | None,
    runner: Callable[[argparse.Namespace], Coroutine[Any, Any, str]],
) -> int:
    """Parses arguments, runs the recipe and prints its answer. Exit code 2 on configuration errors."""
    args = parser.parse_args(argv)
    try:
        answer = asyncio.run(runner(args))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(answer)
    return 0
