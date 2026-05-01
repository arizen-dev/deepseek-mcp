# v0.5.0 — DevEx Upgrades

## Added
- **Cost in metadata footer:** Every response now shows `cost=$0.0001` based on token usage × current pricing.
- **CLI mode:** `python -m deepseek_mcp check|run|advise` for smoke tests and one-shot calls. Exit codes: 0=ok, 1=API error, 2=missing key.
- **Startup key validation:** `initialize` response includes `apiKey` status (set/missing). Stderr hint printed if key is unset. Server stays alive.
- **Call log (opt-in):** Set `DEEPSEEK_MCP_LOG=1` to log call metadata to `~/.deepseek-mcp/calls.jsonl`. No prompts logged.
- **Examples:** `examples/flash_classify.md`, `examples/advise_architecture.md`, `examples/advise_tradeoff.md`.
- **uvx/pipx install paths** documented in README.
- `[project.optional-dependencies] dev = ["pytest>=7"]` in pyproject.toml.

## Changed
- `SERVER_VERSION` → 0.5.0. Package version → 0.5.0.

## Internal
- `_collect_stream` now returns `(text, usage, reasoning_text)` for show-reasoning support.
- `PRICING` dict at module level with current per-model rates.
