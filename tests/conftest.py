from __future__ import annotations

import pytest

# Looks like a real key so masking is exercised; it is not one.
FAKE_KEY = "qd_live_" + "0" * 56 + "deadbeef"


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("QUANTICDATA_API_KEY", FAKE_KEY)
    monkeypatch.delenv("QUANTICDATA_MCP_URL", raising=False)
    monkeypatch.delenv("QUANTICDATA_MCP_TRANSPORT", raising=False)
    return FAKE_KEY


@pytest.fixture
def no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("QUANTICDATA_API_KEY", "QUANTICDATA_MCP_URL", "QUANTICDATA_MCP_TRANSPORT"):
        monkeypatch.delenv(name, raising=False)
