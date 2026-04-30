# Gotchas

## MCP servers start at client launch

If you edit `.mcp.json` or change environment variables, restart Claude Code, Codex, or your MCP client.

## Claude and Codex env handling differ

Claude project MCP configs commonly use:

```json
{
  "env": {
    "DEEPSEEK_API_KEY": "${DEEPSEEK_API_KEY}"
  }
}
```

Codex TOML may not expand that syntax. Prefer explicit env configuration in `~/.codex/config.toml` or your local secret mechanism.

## The server name and tool name are different

Your MCP server can be named `deepseek`, while the tool exposed by that server is also named `deepseek`.

In Claude Code this often appears as:

```text
mcp__deepseek__deepseek
```

## The model is not the owner

DeepSeek is useful for bounded worker tasks. It should not be the final authority on security, architecture, legal, client, or public communication decisions.
