# deepseek-mcp

[![MIT License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![test](https://github.com/arizen-dev/deepseek-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/arizen-dev/deepseek-mcp/actions/workflows/test.yml)

Use DeepSeek from Claude Code, Codex, or any MCP-compatible client as a small, cheap supervised worker.

`deepseek-mcp` is a tiny stdio MCP server with two tools:

```text
deepseek(prompt, system?)     — fast, cheap, non-thinking (flash)
advise(prompt, system?, effort?) — deep reasoning (pro + thinking)
```

It is built for bounded tasks where another model can reduce mechanical load:

- classify inboxes, tickets, logs, notes, or docs;
- summarize packets;
- turn messy text into JSON or tables;
- populate templates;
- generate first-pass mechanical edits;
- produce reviewable candidate output for a human or primary agent.

It is not built for autonomous architecture, security policy, final client prose, or decisions where the hard part is judgment.

## Quickstart

### 1. Install

Zero-install with `uvx`:

```bash
DEEPSEEK_API_KEY="sk-..." uvx deepseek-mcp-server
```

Or install persistently:

```bash
pip install "git+https://github.com/arizen-dev/deepseek-mcp.git"
```

Or clone and install locally:

```bash
git clone https://github.com/arizen-dev/deepseek-mcp.git
cd deepseek-mcp
pip install -e .
```

### 2. Add your DeepSeek key

Create an API key at:

```text
https://platform.deepseek.com/api_keys
```

Then export it:

```bash
export DEEPSEEK_API_KEY="sk-..."
```

For Claude Code, the lowest-friction setup is to put the key in your global settings:

```json
{
  "env": {
    "DEEPSEEK_API_KEY": "sk-..."
  }
}
```

Path:

```text
~/.claude/settings.json
```

MCP servers are started when the client launches, so restart Claude Code or Codex after changing env/config.

### 3. Configure MCP

If you installed via pip (or uvx), use the installed command directly:

```json
{
  "mcpServers": {
    "deepseek": {
      "command": "deepseek-mcp-server",
      "args": [],
      "env": {
        "DEEPSEEK_API_KEY": "${DEEPSEEK_API_KEY}"
      }
    }
  }
}
```

If you cloned the repo, point to the script directly:

```json
{
  "mcpServers": {
    "deepseek": {
      "command": "python3",
      "args": ["/absolute/path/to/deepseek-mcp/deepseek_mcp_server.py"],
      "env": {
        "DEEPSEEK_API_KEY": "${DEEPSEEK_API_KEY}"
      }
    }
  }
}
```

After restart, `/mcp` should show a `deepseek` server.

In Claude Code, the tool names are:

```text
mcp__deepseek__deepseek     — flash (fast, mechanical)
mcp__deepseek__advise       — pro  (deep reasoning)
```

## Codex

For Codex, add a global MCP server in `~/.codex/config.toml`:

```toml
[mcp_servers.deepseekWorker]
command = "deepseek-mcp-server"
args = []

[mcp_servers.deepseekWorker.env]
DEEPSEEK_API_KEY = "sk-..."
```

Codex TOML does not expand `"${DEEPSEEK_API_KEY}"` in the same way Claude project MCP configs do. Put the key directly in the TOML env block or use whatever secret mechanism your Codex environment supports.

## Demo

Prompt:

```text
Classify these files into doc / code / config. Return JSON only:
- README.md
- pyproject.toml
- src/deepseek_mcp/server.py
```

Example output:

```json
[
  {"file": "README.md", "type": "doc"},
  {"file": "pyproject.toml", "type": "config"},
  {"file": "src/deepseek_mcp/server.py", "type": "code"}
]
```

The server appends lightweight metadata:

```text
---
_deepseek · model=deepseek-v4-flash  latency=18.42s  tokens=52+74  cost=$0.0001_
```

Latency depends heavily on prompt size, model, network, and API load. Treat benchmark numbers as directional, not a guarantee.

## CLI

After installing, you can use the CLI for smoke tests and one-shot calls:

```bash
# Validate setup
python -m deepseek_mcp check

# One-shot flash call
python -m deepseek_mcp run "Classify: urgent / later — 'Server down in prod'"

# Advisor call with deep reasoning
python -m deepseek_mcp advise "Should we build or buy analytics?" --effort max
```

Exit codes: 0 = success, 1 = API error, 2 = missing key.

## Models

| Tool | Model | Mode | Best for |
|------|-------|------|----------|
| `deepseek` | deepseek-v4-flash | Non-thinking | Classification, extraction, formatting, mechanical edits |
| `advise` | deepseek-v4-pro | Thinking (effort: medium/high/max) | Architecture, tradeoffs, second opinions, ambiguity |

## Cost

Per-call cost depends on token count and model. Pricing per [api.deepseek.com](https://api.deepseek.com) (checked 2026-04-30).

| Model | Input (miss) | Input (cache hit) | Output |
|-------|-------------|-------------------|--------|
| `deepseek-v4-flash` | $0.14/1M | $0.0028/1M | $0.28/1M |
| `deepseek-v4-pro` | $0.435/1M¹ | $0.0036/1M¹ | $0.87/1M¹ |

¹ Pro pricing is 75% off until 2026-05-31. Non-discounted: $1.74/$0.0145/$3.48.

**Typical per-call cost (cache miss):**

| Task | Flash | Pro |
|------|-------|-----|
| Small (~1K in + ~0.5K out) | ~$0.0003 | ~$0.0009 |
| Medium (~4K in + ~2K out) | ~$0.001 | ~$0.003 |

Each response footer includes an estimated `cost=$...` based on token usage.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | Required. Your DeepSeek API key. |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API base URL (change for proxy/compatible providers). |
| `DEEPSEEK_MCP_LOG` | (unset) | Set to `1` to log call metadata to `~/.deepseek-mcp/calls.jsonl` (no prompts logged). |

## When to use it

Good:

- "Classify these 200 filenames. Mark uncertainty."
- "Turn this rough note into a CSV table."
- "Extract all TODOs and group them by owner."
- "Create candidate JSON from this messy list. Use null for missing values."
- "Summarize this packet for review; do not make decisions."

Bad:

- "Design my architecture."
- "Write the final client email."
- "Decide whether this is secure."
- "Resolve this ambiguous business rule."
- "Publish this reply directly."

Use it like a fast junior analyst whose work you will review, not like an owner.

## How it works

The server:

1. reads JSON-RPC messages from stdin;
2. exposes two MCP tools: `deepseek` (flash, non-thinking) and `advise` (pro, thinking);
3. sends your prompt to DeepSeek's OpenAI-compatible chat completions API;
4. streams the response;
5. returns the text plus model, latency, token, and cost metadata.

There is no database, no background daemon, no local web server, and no file-system access beyond the MCP client starting the process.

## Smoke test

After installing:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  | DEEPSEEK_API_KEY="sk-..." deepseek-mcp-server
```

You should see a JSON response with two tools (`deepseek` + `advise`).

Then test a real call:

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call",\
  "params":{"name":"deepseek","arguments":{"prompt":"Return exactly: ok"}}}' \
  | DEEPSEEK_API_KEY="sk-..." deepseek-mcp-server
```

## Examples

See [examples/](examples/) for real prompt templates:
- [flash_classify.md](examples/flash_classify.md) — inbox triage
- [advise_architecture.md](examples/advise_architecture.md) — architecture decision
- [advise_tradeoff.md](examples/advise_tradeoff.md) — build vs buy

## Benchmark

See [docs/benchmark.md](docs/benchmark.md) for validation observations and usage guidance.

## Development

```bash
pip install -e ".[dev]"
pip install -r requirements-dev.txt  # alternative
python -m pytest
```

## Security notes

- Do not commit API keys.
- Prefer client/global env injection over hardcoding keys in project repos.
- Treat model output as untrusted candidate text.
- Do not give the tool access to secrets you would not paste into DeepSeek directly.
- Review output before it reaches users, customers, production systems, or public channels.

## License

MIT
