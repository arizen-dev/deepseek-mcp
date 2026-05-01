# Workload: deepseek-mcp v0.5 DevEx Upgrades

**Delegated to:** OpenCode + DeepSeek (implementation), Cortex (supervision/review)
**Repo:** `/home/igor/nous/cortex/public-build/deepseek-mcp/` (mirror to `/home/igor/nous/utils/scripts/deepseek_mcp_server.py`)
**Constraint:** Stay zen. No new dependencies unless required. Single-file server stays single-file.

---

## Scope — 7 items, ordered by ROI

### 1. PyPI / `uvx` distribution
- Confirm `pyproject.toml` is publish-ready (it is, version 0.4.0 → bump to 0.5.0 when done).
- Add `[project.scripts]` entry already exists: `deepseek-mcp-server = "deepseek_mcp.server:main"`. Keep.
- Add a `[project.optional-dependencies]` block: `dev = ["pytest>=7"]`.
- Update README "Install" to show:
  - `uvx deepseek-mcp-server` (zero-install run)
  - `pipx install deepseek-mcp` (persistent)
  - dev / from source path
- Do NOT actually publish to PyPI in this workload — Igor decides separately.

### 2. CLI smoke test mode
Add a `__main__.py` (or extend `server.py`) so users can run:
```
python -m deepseek_mcp check        # validates DEEPSEEK_API_KEY, makes 1 cheap flash call, prints OK + latency + tokens
python -m deepseek_mcp run "prompt" # one-shot flash call, prints response
python -m deepseek_mcp advise "prompt" [--effort max|high|medium] [--show-reasoning]
```
- Reuses `call_deepseek` / `call_advisor`.
- `--show-reasoning` only on advise; pulls `reasoning_content` from delta if present (currently dropped — add a flag-gated capture).
- Exit code 0 on success, 1 on API error, 2 on missing key.
- Keep argparse minimal (stdlib only).

### 3. Cost estimate in metadata footer
- Add a small `PRICING` dict at top of `server.py`:
  ```python
  PRICING = {
      "deepseek-v4-flash":  {"in": 0.14, "out": 0.28},   # $/1M tokens, full price
      "deepseek-v4-pro":    {"in": 0.435, "out": 1.74},  # discounted until 2026-05-31; full: 1.74 / 6.96
  }
  ```
- In `_format_result`, when usage present, compute `cost ≈ (prompt*in + completion*out) / 1_000_000` and append `cost≈$0.0001` to the metadata line.
- Round to 4 significant figures, never display `$0.0000` — clamp to `<$0.0001`.
- Note: pricing is informational only; do not gate calls.

### 4. Startup key validation
- On `initialize` request, if `DEEPSEEK_API_KEY` is empty, return a clear error in `serverInfo` *and* log to stderr a one-line hint:
  `deepseek-mcp: DEEPSEEK_API_KEY not set. Get a key at platform.deepseek.com and add to your MCP config env.`
- Do NOT crash — MCP clients show server as "failed to start" which is unhelpful. Stay alive, surface error on first tool call too.

### 5. `--show-reasoning` for advise (also exposed via CLI item 2)
- Capture `delta.reasoning_content` in `_collect_stream` into a separate `reasoning` string.
- Add optional `show_reasoning: bool` param to `advise` tool inputSchema (default false).
- When true, prepend `<reasoning>...</reasoning>` block to the response before CONCLUSION.

### 6. Optional call log
- If env `DEEPSEEK_MCP_LOG=1`, append one JSON line per call to `~/.deepseek-mcp/calls.jsonl`:
  `{"ts": "...", "tool": "deepseek|advise", "model": "...", "effort": "...", "tokens_in": N, "tokens_out": N, "latency_s": N, "cost_usd": N}`
- Create dir if missing. Never log prompt content (privacy).
- Off by default. Document in README.

### 7. Examples folder
- Add `examples/`:
  - `flash_classify.md` — prompt + expected shape for inbox triage
  - `advise_architecture.md` — example prompt for second-opinion use
  - `advise_tradeoff.md` — example A vs B decision
- Keep each <40 lines. Real prompts, not lorem ipsum.

---

## What NOT to do
- No plugin system, no multi-turn state, no web UI, no rate limiting, no streaming-to-stdout outside MCP frames.
- No new runtime deps. (`openai>=1.0` only.)
- No refactor for refactor's sake. Single-file server stays single-file (CLI can be a sibling module).

---

## Acceptance Criteria
- [ ] `python -m deepseek_mcp check` passes against real API
- [ ] `python -m deepseek_mcp run "say hi"` returns text + footer with `cost≈$...`
- [ ] `python -m deepseek_mcp advise "..." --show-reasoning` shows reasoning block
- [ ] Existing `tests/test_protocol.py` still passes
- [ ] README updated with: install via uvx/pipx, CLI usage, env vars table (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MCP_LOG`), pricing/cost note, examples link
- [ ] `pyproject.toml` version bumped to `0.5.0`
- [ ] `SERVER_VERSION` in server.py bumped to `0.5.0`
- [ ] No new dependencies in `pyproject.toml`
- [ ] `git diff --stat` < 600 lines added (zen check)

---

## Deliverables
1. Modified `src/deepseek_mcp/server.py`
2. New `src/deepseek_mcp/__main__.py` (or CLI integrated into server.py — your call, justify briefly)
3. Updated `pyproject.toml`
4. Updated `README.md`
5. New examples under `examples/`
6. Mirror final server.py to `/home/igor/nous/utils/scripts/deepseek_mcp_server.py` (single-file variant — keep CLI inline there since it has no package)
7. Brief `CHANGELOG_v0.5.md` summarizing changes
8. Do NOT git commit or push — Cortex reviews first

---

## Questions to flag (don't guess)
- If pricing changes after May 31, where should the source of truth live? (suggestion: keep in code with a comment, update on next release)
- If `reasoning_content` field name differs in actual DeepSeek API response vs what we assume, surface that in your report rather than silently failing.

---

*Cortex will review the diff, run the smoke tests, and merge/push.*
