# Contributing

## Issues

Bug reports and feature requests are welcome. Use the GitHub issue templates.

## Pull requests

Keep PRs focused on a single concern. Open an issue first if the change is non-trivial.

## Feedback

If deepseek-mcp worked well (or badly) for a task, consider dropping a note in an issue. Real usage reports help more than synthetic benchmarks.

## Design principles

- Zero surprise behavior — no telemetry, no phoning home, no hidden state.
- Fail visibly — errors should be clear and actionable.
- One tool, one responsibility — `deepseek` takes a prompt and returns text. No file ops, no plugins.
- MCP stdio only — no HTTP, no daemon, no database.
