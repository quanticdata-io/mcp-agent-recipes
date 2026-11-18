# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Email **hello@quanticdata.io** with the subject "Security: mcp-agent-recipes" and include a description, steps to reproduce and the recipe concerned. We acknowledge reports within 3 business days and keep you informed until a fix is released.

## API keys

The recipes read `QUANTICDATA_API_KEY` from the environment and send it only to the MCP endpoint (`QUANTICDATA_MCP_URL`, default `https://api.quanticdata.io/mcp`) in the `Authorization` header, or pass it to the local `quanticdata-mcp` subprocess in its environment. The local subprocess gets the MCP SDK's minimal default environment plus that key, not your whole environment, so other keys (for example `OPENAI_API_KEY`) are not passed to it. `QuanticDataMCP` masks the key in `repr()` and `str()`.

Never commit a key; keep it in your shell or a `.env` file that git ignores. If a key leaks, rotate it on the API keys page of the QuanticData dashboard. Model provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are read by the frameworks themselves.
