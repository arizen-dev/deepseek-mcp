# deepseek-mcp

[![MIT License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![test](https://github.com/arizen-dev/deepseek-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/arizen-dev/deepseek-mcp/actions/workflows/test.yml)

Use DeepSeek from Claude Code, Codex, or any MCP-compatible client as a small, cheap supervised worker.

`deepseek-mcp` is a tiny stdio MCP server with one tool:

```text
deepseek(prompt, system?, model?)
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

Clone and install locally:

```bash
git clone https://github.com/arizen-dev/deepseek-mcp.git
cd deepseek-mcp
python3 -m pip install -e .
```

Or install directly from GitHub:

```bash
python3 -m pip install "git+https://github.com/arizen-dev/deepseek-mcp.git"
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

For a project-local Claude Code setup, copy `.mcp.json.example` to `.mcp.json` and set the absolute path:

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

In Claude Code, the tool name is usually:

```text
mcp__deepseek__deepseek
```

## Codex

For Codex, add a global MCP server in `~/.codex/config.toml`:

```toml
[mcp_servers.deepseekWorker]
command = "python3"
args = ["/absolute/path/to/deepseek-mcp/deepseek_mcp_server.py"]

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
_deepseek · model=deepseek-v4-flash  latency=18.42s  tokens=52+74_
```

Latency depends heavily on prompt size, model, network, and API load. In local doc-ops style checks, small structured tasks were typically tens of seconds; tiny smoke tests can return much faster. Treat benchmark numbers as directional, not a guarantee.

## Models

The default model is:

```text
deepseek-v4-flash
```

You can request:

```json
{
  "model": "deepseek-v4-pro",
  "prompt": "..."
}
```

Model names are passed through to the DeepSeek-compatible API. If DeepSeek changes model names, update the `model` argument.

## Cost

Per-call cost depends on token count and model. Pricing per [api.deepseek.com](https://api.deepseek.com) (checked 2026-04-30).

| Model | Input (miss) | Input (cache hit) | Output |
|-------|-------------|-------------------|--------|
| `deepseek-v4-flash` | $0.14/1M | $0.0028/1M | $0.28/1M |
| `deepseek-v4-pro` | $0.435/1M¹ | $0.0036/1M¹ | $0.87/1M¹ |

¹ Pro pricing is 75% off until 2026-05-31. Non-discounted: $1.74/$0.0145/$3.48.

**Typical costs:**

| Task | Flash (cache miss) | Flash (cache hit) | Pro (cache miss) |
|------|-------------------|-------------------|-------------------|
| Small (1K+0.5K) | ~$0.0003 | ~$0.0001 | ~$0.0009 |
| Medium (4K+2K) | ~$0.001 | ~$0.0006 | ~$0.003 |
| Large (100K+10K) | ~$0.02 | ~$0.003 | ~$0.05 |

A session of 100 small tasks costs roughly $0.03 (flash) or $0.09 (pro).

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
2. exposes one MCP tool named `deepseek`;
3. sends your prompt to DeepSeek's OpenAI-compatible chat completions API;
4. streams the response;
5. returns the text plus model, latency, and token metadata.

There is no database, no background daemon, no local web server, and no file-system access beyond the MCP client starting the process.

## Smoke test

After installing:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  | DEEPSEEK_API_KEY="sk-..." python3 deepseek_mcp_server.py
```

You should see a JSON response with a single `deepseek` tool.

Then test a real call:

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"deepseek","arguments":{"prompt":"Return exactly: ok"}}}' \
  | DEEPSEEK_API_KEY="sk-..." python3 deepseek_mcp_server.py
```

## Benchmark

See [docs/benchmark.md](docs/benchmark.md) for validation observations and usage guidance.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

If you do not install dev extras:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

## Security notes

- Do not commit API keys.
- Prefer client/global env injection over hardcoding keys in project repos.
- Treat model output as untrusted candidate text.
- Do not give the tool access to secrets you would not paste into DeepSeek directly.
- Review output before it reaches users, customers, production systems, or public channels.

## License

MIT
